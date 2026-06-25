from pathlib import Path

from fastapi.testclient import TestClient


def create_song(client: TestClient) -> dict[str, object]:
    response = client.post(f"/api/organizations/{client.organization_id}/admin/songs", json={"title": "Demo Song", "slug": "demo-song"})
    assert response.status_code == 201
    return response.json()


def test_wav_upload_and_delete_cleanup(client: TestClient) -> None:
    song = create_song(client)

    upload_response = client.post(
        f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}/stems/upload",
        data={"name": "Drums", "role": "drums", "key": "0"},
        files={"file": ("drums.wav", b"RIFF----WAVEfmt data", "audio/wav")},
    )
    assert upload_response.status_code == 201
    stem = upload_response.json()
    assert stem["songId"] == song["id"]
    assert stem["status"] == "uploaded"
    assert stem["key"] == 0
    assert stem["sourceFilename"] == "drums.wav"
    assert stem["fileSizeBytes"] == 20

    storage = client.storage  # type: ignore[attr-defined]
    source_path = storage.source_path(client.organization_id, song["id"], stem["id"])  # type: ignore[attr-defined]
    assert source_path.read_bytes() == b"RIFF----WAVEfmt data"

    list_response = client.get(f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}/stems")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [stem["id"]]

    invalid_response = client.post(
        f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}/stems/upload",
        data={"name": "MP3", "role": "other"},
        files={"file": ("bad.mp3", b"not wav", "audio/mpeg")},
    )
    assert invalid_response.status_code == 400

    delete_response = client.delete(
        f"/api/organizations/{client.organization_id}/admin/stems/{stem['id']}"
    )
    assert delete_response.status_code == 204
    assert not source_path.exists()


def test_song_cleanup_removes_uploaded_stems(client: TestClient) -> None:
    song = create_song(client)
    storage = client.storage  # type: ignore[attr-defined]

    upload_response = client.post(
        f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}/stems/upload",
        data={"name": "Vocals", "role": "vocals"},
        files={"file": ("vocals.wav", b"RIFF-upload-WAVE", "audio/wav")},
    )
    assert upload_response.status_code == 201
    stem = upload_response.json()
    assert stem["key"] is None
    assert stem["sourceFilename"] == "vocals.wav"
    assert stem["fileSizeBytes"] == 16

    uploaded_file = storage.source_path(client.organization_id, song["id"], stem["id"])  # type: ignore[attr-defined]
    assert uploaded_file.read_bytes() == b"RIFF-upload-WAVE"

    delete_song_response = client.delete(f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}")
    assert delete_song_response.status_code == 204
    assert not storage.song_dir(client.organization_id, song["id"]).exists()  # type: ignore[attr-defined]


def test_source_import_endpoints_are_removed(client: TestClient) -> None:
    song = create_song(client)
    payload = {"sourcePath": "vocals.wav", "name": "Vocals", "role": "vocals"}

    assert client.post(f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}/stems/import", json=payload).status_code == 404
    assert client.post(f"/api/organizations/{client.organization_id}/admin/songs/{song['id']}/stems/import", json=payload).status_code == 404
