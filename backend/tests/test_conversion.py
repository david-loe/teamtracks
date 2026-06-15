import io
import json
import subprocess
import wave
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.services.conversion import ConversionService


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
    mono_output = Path(storage.storage_root) / "songs" / str(song["id"]) / "converted" / f"{mono_stem['id']}.m4a"
    stereo_output = Path(storage.storage_root) / "songs" / str(song["id"]) / "converted" / f"{stereo_stem['id']}.m4a"
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
