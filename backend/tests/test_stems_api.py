from pathlib import Path

from fastapi.testclient import TestClient


def create_song(client: TestClient) -> dict[str, object]:
    response = client.post("/api/songs", json={"title": "Demo Song", "slug": "demo-song"})
    assert response.status_code == 201
    return response.json()


def test_wav_upload_and_delete_cleanup(client: TestClient) -> None:
    song = create_song(client)

    upload_response = client.post(
        f"/api/songs/{song['id']}/stems/upload",
        data={"name": "Drums", "role": "drums"},
        files={"file": ("drums.wav", b"RIFF----WAVEfmt data", "audio/wav")},
    )
    assert upload_response.status_code == 201
    stem = upload_response.json()
    assert stem["songId"] == song["id"]
    assert stem["status"] == "uploaded"
    assert stem["sourceFilename"] == "drums.wav"
    assert stem["fileSizeBytes"] == 20

    storage = client.storage  # type: ignore[attr-defined]
    source_path = Path(storage.storage_root) / "songs" / str(song["id"]) / "source" / f"{stem['id']}.wav"
    assert source_path.read_bytes() == b"RIFF----WAVEfmt data"

    list_response = client.get(f"/api/songs/{song['id']}/stems")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [stem["id"]]

    invalid_response = client.post(
        f"/api/songs/{song['id']}/stems/upload",
        data={"name": "MP3", "role": "other"},
        files={"file": ("bad.mp3", b"not wav", "audio/mpeg")},
    )
    assert invalid_response.status_code == 400

    delete_response = client.delete(f"/api/stems/{stem['id']}")
    assert delete_response.status_code == 204
    assert not source_path.exists()


def test_secure_import_and_song_cleanup(client: TestClient, tmp_path: Path) -> None:
    song = create_song(client)
    storage = client.storage  # type: ignore[attr-defined]

    import_file = Path(storage.source_root) / "demo" / "vocals.wav"
    import_file.parent.mkdir(parents=True)
    import_file.write_bytes(b"RIFF-import-WAVE")

    import_response = client.post(
        f"/api/songs/{song['id']}/stems/import",
        json={"sourcePath": str(import_file), "name": "Vocals", "role": "vocals"},
    )
    assert import_response.status_code == 201
    stem = import_response.json()
    assert stem["sourceFilename"] == "vocals.wav"
    assert stem["fileSizeBytes"] == 16

    copied_file = Path(storage.storage_root) / "songs" / str(song["id"]) / "source" / f"{stem['id']}.wav"
    assert copied_file.read_bytes() == b"RIFF-import-WAVE"

    outside_file = tmp_path / "outside.wav"
    outside_file.write_bytes(b"outside")
    outside_response = client.post(
        f"/api/songs/{song['id']}/stems/import",
        json={"sourcePath": str(outside_file), "name": "Outside", "role": "other"},
    )
    assert outside_response.status_code == 400

    non_wav = Path(storage.source_root) / "demo" / "notes.txt"
    non_wav.write_text("not audio")
    non_wav_response = client.post(
        f"/api/songs/{song['id']}/stems/import",
        json={"sourcePath": str(non_wav), "name": "Notes", "role": "other"},
    )
    assert non_wav_response.status_code == 400

    delete_song_response = client.delete(f"/api/songs/{song['id']}")
    assert delete_song_response.status_code == 204
    assert not (Path(storage.storage_root) / "songs" / str(song["id"])).exists()
