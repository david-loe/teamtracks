import io
import json
import subprocess
import wave
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.services.conversion import ConversionService
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.models.stem_key_asset import StemKeyAsset


def create_song(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/songs", json={"title": "Conversion Song", "slug": "conversion-song"})
    assert response.status_code == 201
    return response.json()


def wav_bytes(*, channels: int, sample_rate: int = 44100, duration_ms: int = 500) -> bytes:
    buffer = io.BytesIO()
    frame_count = round(sample_rate * duration_ms / 1000)
    silence_frame = b"\x00\x00" * channels
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(silence_frame * frame_count)
    return buffer.getvalue()


def upload_stem(
    client: TestClient,
    song_id: int,
    *,
    name: str,
    role: str = "other",
    channels: int = 2,
    sample_rate: int = 44100,
    duration_ms: int = 500,
) -> dict[str, Any]:
    response = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"name": name, "role": role},
        files={"file": (f"{name}.wav", wav_bytes(channels=channels, sample_rate=sample_rate, duration_ms=duration_ms), "audio/wav")},
    )
    assert response.status_code == 201
    return response.json()


def process_jobs(client: TestClient, job_ids: list[int]) -> None:
    storage = client.storage  # type: ignore[attr-defined]
    session_factory = client.session_factory  # type: ignore[attr-defined]
    for job_id in job_ids:
        with session_factory() as db:
            ConversionService(storage).process_job(db, job_id)


def probe_audio(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def first_audio_stream(payload: dict[str, Any]) -> dict[str, Any]:
    return next(stream for stream in payload["streams"] if stream["codec_type"] == "audio")


def test_conversion_jobs_convert_mono_and_stereo_to_m4a(client: TestClient) -> None:
    song = create_song(client)
    mono_stem = upload_stem(client, song["id"], name="vocals", role="vocals", channels=1, sample_rate=48000)
    stereo_stem = upload_stem(client, song["id"], name="drums", role="drums", channels=2, sample_rate=48000)

    create_response = client.post(f"/api/songs/{song['id']}/conversion-jobs", json={})
    assert create_response.status_code == 201
    job_ids = create_response.json()["jobIds"]
    assert len(job_ids) == 2

    process_jobs(client, job_ids)

    jobs_response = client.get(f"/api/songs/{song['id']}/conversion-jobs")
    assert jobs_response.status_code == 200
    assert {job["status"] for job in jobs_response.json()} == {"succeeded"}

    song_response = client.get(f"/api/songs/{song['id']}")
    assert song_response.status_code == 200
    assert song_response.json()["status"] == "ready"
    assert song_response.json()["targetSampleRate"] == 48000
    assert song_response.json()["targetDurationMs"] == 500

    stems_response = client.get(f"/api/songs/{song['id']}/stems")
    assert stems_response.status_code == 200
    stems = {stem["id"]: stem for stem in stems_response.json()}
    assert stems[mono_stem["id"]]["status"] == "ready"
    assert stems[mono_stem["id"]]["codec"] == "aac-lc"
    assert stems[mono_stem["id"]]["channels"] == 1
    assert stems[mono_stem["id"]]["bitrateKbps"] == 96
    assert stems[stereo_stem["id"]]["status"] == "ready"
    assert stems[stereo_stem["id"]]["channels"] == 2
    assert stems[stereo_stem["id"]]["bitrateKbps"] == 160

    storage = client.storage  # type: ignore[attr-defined]
    manifest = client.get(f"/api/songs/{song['id']}/manifest").json()
    selected_key_id = manifest["selectedKeyId"]
    mono_output = Path(storage.storage_root) / "songs" / str(song["id"]) / "keys" / str(selected_key_id) / f"{mono_stem['id']}.m4a"
    stereo_output = Path(storage.storage_root) / "songs" / str(song["id"]) / "keys" / str(selected_key_id) / f"{stereo_stem['id']}.m4a"
    assert mono_output.is_file()
    assert stereo_output.is_file()
    assert first_audio_stream(probe_audio(mono_output))["channels"] == 1
    assert first_audio_stream(probe_audio(stereo_output))["channels"] == 2


def test_conversion_rejects_multichannel_input(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"], name="surround", channels=4)

    create_response = client.post(f"/api/songs/{song['id']}/conversion-jobs", json={"stemIds": [stem["id"]]})
    assert create_response.status_code == 201
    job_id = create_response.json()["jobIds"][0]

    process_jobs(client, [job_id])

    job_response = client.get(f"/api/conversion-jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "failed"
    assert "mono and stereo" in job_response.json()["errorMessage"]

    stems_response = client.get(f"/api/songs/{song['id']}/stems")
    assert stems_response.status_code == 200
    converted_stem = stems_response.json()[0]
    assert converted_stem["status"] == "error"
    assert "mono and stereo" in converted_stem["errorMessage"]


def test_duration_difference_within_tolerance_is_normalized(client: TestClient) -> None:
    song = create_song(client)
    long_stem = upload_stem(client, song["id"], name="reference", duration_ms=1000)
    short_stem = upload_stem(client, song["id"], name="short", duration_ms=930)

    create_response = client.post(f"/api/songs/{song['id']}/conversion-jobs", json={})
    assert create_response.status_code == 201
    process_jobs(client, create_response.json()["jobIds"])

    stems_response = client.get(f"/api/songs/{song['id']}/stems")
    assert stems_response.status_code == 200
    stems = {stem["id"]: stem for stem in stems_response.json()}
    assert stems[long_stem["id"]]["status"] == "ready"
    assert stems[short_stem["id"]]["status"] == "ready"
    assert stems[long_stem["id"]]["durationMs"] == 1000
    assert stems[short_stem["id"]]["durationMs"] == 1000


def test_duration_difference_over_tolerance_marks_stem_error(client: TestClient) -> None:
    song = create_song(client)
    upload_stem(client, song["id"], name="reference", duration_ms=1000)
    short_stem = upload_stem(client, song["id"], name="too-short", duration_ms=850)

    create_response = client.post(f"/api/songs/{song['id']}/conversion-jobs", json={})
    assert create_response.status_code == 201
    process_jobs(client, create_response.json()["jobIds"])

    stems_response = client.get(f"/api/songs/{song['id']}/stems")
    assert stems_response.status_code == 200
    stems = {stem["id"]: stem for stem in stems_response.json()}
    assert stems[short_stem["id"]]["status"] == "error"
    assert "maximum allowed is 100 ms" in stems[short_stem["id"]]["errorMessage"]

    song_response = client.get(f"/api/songs/{song['id']}")
    assert song_response.status_code == 200
    assert song_response.json()["status"] == "error"


def test_transpose_song_creates_target_key_assets_and_reuses_keyless_stems(client: TestClient) -> None:
    song = create_song(client)
    drums = upload_stem(client, song["id"], name="drums", role="drums", channels=2, sample_rate=48000)
    bass = upload_stem(client, song["id"], name="bass", role="bass", channels=1, sample_rate=48000)

    session_factory = client.session_factory  # type: ignore[attr-defined]
    with session_factory() as db:
        bass_stem = db.get(Stem, bass["id"])
        assert bass_stem is not None
        bass_stem.key = 0
        db.commit()

    create_response = client.post(f"/api/songs/{song['id']}/conversion-jobs", json={})
    assert create_response.status_code == 201
    process_jobs(client, create_response.json()["jobIds"])

    transpose_response = client.post(f"/api/admin/songs/{song['id']}/transpose", json={"targetKeys": [2]})
    assert transpose_response.status_code == 200
    transpose_jobs = transpose_response.json()
    assert transpose_jobs["status"] == "queued"
    assert len(transpose_jobs["jobIds"]) == 1

    with session_factory() as db:
        assert db.query(SongKey).filter_by(song_id=song["id"], semitone_offset=2).one_or_none() is None

    process_jobs(client, transpose_jobs["jobIds"])

    job_response = client.get(f"/api/admin/conversion-jobs/{transpose_jobs['jobIds'][0]}")
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["jobType"] == "song_transposition"
    assert job["targetKey"] == 2
    assert job["semitoneOffset"] == 2
    assert job["status"] == "succeeded"
    assert job["songKeyId"] is not None
    target_key = {"id": job["songKeyId"]}

    manifest_response = client.get(f"/api/admin/songs/{song['id']}/manifest", params={"keyId": target_key["id"]})
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    assert manifest["selectedKeyId"] == target_key["id"]
    assert manifest["playable"] is True
    assert {stem["id"]: stem["url"] for stem in manifest["stems"]} == {
        drums["id"]: f"/media/songs/{song['id']}/keys/{target_key['id']}/stems/{drums['id']}.m4a",
        bass["id"]: f"/media/songs/{song['id']}/keys/{target_key['id']}/stems/{bass['id']}.m4a",
    }

    storage = client.storage  # type: ignore[attr-defined]
    with session_factory() as db:
        original_key = db.query(SongKey).filter_by(song_id=song["id"], semitone_offset=0).one()
        target_key_model = db.query(SongKey).filter_by(song_id=song["id"], semitone_offset=2).one()
        original_drums_asset = db.query(StemKeyAsset).filter_by(song_key_id=original_key.id, stem_id=drums["id"]).one()
        target_drums_asset = db.query(StemKeyAsset).filter_by(song_key_id=target_key_model.id, stem_id=drums["id"]).one()
        target_bass_asset = db.query(StemKeyAsset).filter_by(song_key_id=target_key_model.id, stem_id=bass["id"]).one()
        assert target_drums_asset.file_path == original_drums_asset.file_path
        assert target_bass_asset.file_path == str(storage.key_asset_path(song["id"], target_key_model.id, bass["id"]))
        assert Path(target_bass_asset.file_path).is_file()

    inventory_response = client.get(f"/api/admin/songs/{song['id']}/key-assets")
    assert inventory_response.status_code == 200
    inventory = {item["stemId"]: item for item in inventory_response.json()}
    assert {variant["targetKey"] for variant in inventory[drums["id"]]["variants"]} == {0, 2}
    assert {variant["targetKey"] for variant in inventory[bass["id"]]["variants"]} == {0, 2}
    assert all(variant["status"] == "ready" for item in inventory.values() for variant in item["variants"])


def test_transpose_job_failure_marks_job_and_song_key_error(client: TestClient) -> None:
    song = create_song(client)
    bass = upload_stem(client, song["id"], name="bass", role="bass", channels=1, sample_rate=48000)

    session_factory = client.session_factory  # type: ignore[attr-defined]
    with session_factory() as db:
        bass_stem = db.get(Stem, bass["id"])
        assert bass_stem is not None
        bass_stem.key = 0
        db.commit()

    create_response = client.post(f"/api/songs/{song['id']}/conversion-jobs", json={})
    assert create_response.status_code == 201
    process_jobs(client, create_response.json()["jobIds"])

    transpose_response = client.post(f"/api/admin/songs/{song['id']}/transpose", json={"targetKeys": [2]})
    assert transpose_response.status_code == 200
    job_id = transpose_response.json()["jobIds"][0]

    with session_factory() as db:
        bass_stem = db.get(Stem, bass["id"])
        assert bass_stem is not None
        bass_stem.source_path = str(Path(bass_stem.source_path or "").with_name("missing.wav"))
        db.commit()

    process_jobs(client, [job_id])

    job_response = client.get(f"/api/admin/conversion-jobs/{job_id}")
    assert job_response.status_code == 200
    failed_job = job_response.json()
    assert failed_job["status"] == "failed"
    assert failed_job["errorMessage"]
    assert failed_job["songKeyId"] is not None

    with session_factory() as db:
        song_key = db.get(SongKey, failed_job["songKeyId"])
        assert song_key is not None
        assert song_key.status == "error"
        assert song_key.error_message == failed_job["errorMessage"]


def test_original_key_change_relabels_relative_key_variants_without_reprocessing(client: TestClient) -> None:
    song = create_song(client)
    upload_stem(client, song["id"], name="drums", role="drums", channels=2, sample_rate=48000)
    create_response = client.post(f"/api/songs/{song['id']}/conversion-jobs", json={})
    assert create_response.status_code == 201
    process_jobs(client, create_response.json()["jobIds"])

    transpose_response = client.post(f"/api/admin/songs/{song['id']}/transpose", json={"targetKeys": [2]})
    assert transpose_response.status_code == 200
    transpose_job_id = transpose_response.json()["jobIds"][0]
    process_jobs(client, [transpose_job_id])
    target_variant = client.get(f"/api/admin/conversion-jobs/{transpose_job_id}").json()

    update_response = client.patch(f"/api/admin/songs/{song['id']}", json={"originalKey": 5})
    assert update_response.status_code == 200
    assert update_response.json()["originalKey"] == 5

    manifest_response = client.get(f"/api/admin/songs/{song['id']}/manifest", params={"keyId": target_variant["songKeyId"]})
    assert manifest_response.status_code == 200
    manifest = manifest_response.json()
    variants = {variant["id"]: variant for variant in manifest["keyVariants"]}
    assert manifest["song"]["originalKey"] == 5
    assert variants[manifest["selectedKeyId"]]["semitoneOffset"] == 2
