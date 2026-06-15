from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.domain import SongStatus, StemStatus
from app.models.song import Song
from app.models.stem import Stem


def create_song(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/songs", json={"title": "Manifest Song", "slug": "manifest-song"})
    assert response.status_code == 201
    return response.json()


def upload_stem(client: TestClient, song_id: int, *, name: str = "drums", role: str = "drums") -> dict[str, Any]:
    response = client.post(
        f"/api/songs/{song_id}/stems/upload",
        data={"name": name, "role": role},
        files={"file": (f"{name}.wav", b"RIFF----WAVEfmt data", "audio/wav")},
    )
    assert response.status_code == 201
    return response.json()


def mark_stem_ready(client: TestClient, song_id: int, stem_id: int, *, write_file: bool = True) -> Path:
    storage = client.storage  # type: ignore[attr-defined]
    converted_path = Path(storage.storage_root) / "songs" / str(song_id) / "converted" / f"{stem_id}.m4a"
    if write_file:
        converted_path.parent.mkdir(parents=True, exist_ok=True)
        converted_path.write_bytes(b"m4a-data")

    session_factory = client.session_factory  # type: ignore[attr-defined]
    with session_factory() as db:
        song = db.get(Song, song_id)
        stem = db.get(Stem, stem_id)
        assert song is not None
        assert stem is not None
        song.status = SongStatus.READY.value
        song.target_sample_rate = 48000
        song.target_duration_ms = 184320
        stem.status = StemStatus.READY.value
        stem.converted_path = str(converted_path)
        stem.codec = "aac-lc"
        stem.channels = 2
        stem.sample_rate = 48000
        stem.duration_ms = 184320
        stem.file_size_bytes = 2210340
        stem.bitrate_kbps = 160
        db.commit()

    return converted_path


def test_manifest_includes_ready_playback_stems(client: TestClient) -> None:
    song = create_song(client)
    ready_stem = upload_stem(client, song["id"], name="drums", role="drums")
    mark_stem_ready(client, song["id"], ready_stem["id"])

    response = client.get(f"/api/songs/{song['id']}/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["song"] == {
        "id": song["id"],
        "title": "Manifest Song",
        "slug": "manifest-song",
        "durationMs": 184320,
        "sampleRate": 48000,
    }
    assert manifest["playable"] is True
    assert manifest["stems"] == [
        {
            "id": ready_stem["id"],
            "name": "drums",
            "role": "drums",
            "status": "ready",
            "url": f"/media/songs/{song['id']}/stems/{ready_stem['id']}.m4a",
            "codec": "aac-lc",
            "container": "m4a",
            "channels": 2,
            "sampleRate": 48000,
            "durationMs": 184320,
            "fileSizeBytes": 2210340,
            "bitrateKbps": 160,
            "errorMessage": None,
        }
    ]


def test_manifest_is_not_playable_with_non_ready_stems(client: TestClient) -> None:
    song = create_song(client)
    ready_stem = upload_stem(client, song["id"], name="drums", role="drums")
    pending_stem = upload_stem(client, song["id"], name="vocals", role="vocals")
    mark_stem_ready(client, song["id"], ready_stem["id"])

    response = client.get(f"/api/songs/{song['id']}/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["playable"] is False
    stems = {stem["id"]: stem for stem in manifest["stems"]}
    assert stems[ready_stem["id"]]["url"] == f"/media/songs/{song['id']}/stems/{ready_stem['id']}.m4a"
    assert stems[pending_stem["id"]]["status"] == "uploaded"
    assert stems[pending_stem["id"]]["url"] is None
    assert stems[pending_stem["id"]]["codec"] is None


def test_media_serves_ready_m4a_with_headers(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"])
    mark_stem_ready(client, song["id"], stem["id"])

    url = f"/media/songs/{song['id']}/stems/{stem['id']}.m4a"
    response = client.get(url)
    assert response.status_code == 200
    assert response.content == b"m4a-data"
    assert response.headers["content-type"].startswith("audio/mp4")
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.headers["accept-ranges"] == "bytes"

    range_response = client.get(url, headers={"Range": "bytes=0-2"})
    assert range_response.status_code == 206
    assert range_response.content == b"m4a"
    assert range_response.headers["content-range"] == "bytes 0-2/8"


def test_media_rejects_missing_and_not_ready_files(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"])

    not_ready_response = client.get(f"/media/songs/{song['id']}/stems/{stem['id']}.m4a")
    assert not_ready_response.status_code == 409

    mark_stem_ready(client, song["id"], stem["id"], write_file=False)
    missing_file_response = client.get(f"/media/songs/{song['id']}/stems/{stem['id']}.m4a")
    assert missing_file_response.status_code == 404

    wrong_song_response = client.get(f"/media/songs/{song['id'] + 1}/stems/{stem['id']}.m4a")
    assert wrong_song_response.status_code == 404
