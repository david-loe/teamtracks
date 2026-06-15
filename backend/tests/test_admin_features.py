from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.models.conversion_job import ConversionJob
from app.models.song import Song
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.models.stem_key_asset import StemKeyAsset
from app.services.auth import create_admin_token, is_valid_admin_token, require_admin_session


SETTINGS = {
    "monoBitrateKbps": 112,
    "stereoBitrateKbps": 192,
    "targetSampleRate": 44100,
    "durationToleranceMs": 250,
    "stemGainDefaultDb": -2,
    "stemGainMinDb": -30,
    "stemGainMaxDb": 4,
    "stemGainStepDb": 2,
    "focusGainDefaultDb": 1,
    "focusGainMinDb": -10,
    "focusGainMaxDb": 5,
    "backgroundGainDefaultDb": -15,
    "backgroundGainMinDb": -30,
    "backgroundGainMaxDb": -1,
}


def test_admin_session_protects_admin_api(client: TestClient) -> None:
    override = app.dependency_overrides.pop(require_admin_session)
    try:
        assert client.get("/api/admin/songs").status_code == 401
        assert client.post("/api/admin/session", json={"password": "wrong"}).status_code == 401
        login = client.post(
            "/api/admin/session",
            json={"password": get_settings().admin_password.get_secret_value()},
        )
        assert login.status_code == 200
        assert login.json() == {"authenticated": True}
        assert "HttpOnly" in login.headers["set-cookie"]
        assert "SameSite=lax" in login.headers["set-cookie"]
        assert client.get("/api/admin/session").status_code == 200
        assert client.get("/api/admin/songs").status_code == 200
        assert client.delete("/api/admin/session").status_code == 204
        assert client.get("/api/admin/session").status_code == 401
    finally:
        app.dependency_overrides[require_admin_session] = override


def test_admin_tokens_reject_tampering_and_expiration() -> None:
    settings = get_settings()
    token = create_admin_token(settings, now=100)
    assert is_valid_admin_token(token, settings, now=101)
    assert not is_valid_admin_token(f"{token}x", settings, now=101)
    assert not is_valid_admin_token(token, settings, now=100 + settings.admin_session_hours * 3600)


def test_settings_validation_and_job_snapshot(client: TestClient) -> None:
    response = client.put("/api/admin/settings", json=SETTINGS)
    assert response.status_code == 200
    assert response.json() == SETTINGS

    invalid = {**SETTINGS, "stemGainDefaultDb": -40}
    assert client.put("/api/admin/settings", json=invalid).status_code == 422

    song = client.post("/api/admin/songs", json={"title": "Snapshot", "slug": "snapshot"}).json()
    upload = client.post(
        f"/api/admin/songs/{song['id']}/stems/upload",
        data={"name": "Stem", "role": "other"},
        files={"file": ("stem.wav", b"RIFF----WAVEfmt data", "audio/wav")},
    )
    stem = upload.json()
    jobs = client.post(
        f"/api/admin/songs/{song['id']}/conversion-jobs", json={"stemIds": [stem["id"]]}
    ).json()

    changed = {**SETTINGS, "monoBitrateKbps": 80, "targetSampleRate": 48000}
    assert client.put("/api/admin/settings", json=changed).status_code == 200

    with client.session_factory() as db:  # type: ignore[attr-defined]
        job = db.get(ConversionJob, jobs["jobIds"][0])
        assert job is not None
        assert job.mono_bitrate_kbps == 112
        assert job.target_sample_rate == 44100


def test_public_search_and_manifest_only_expose_playable_songs(client: TestClient) -> None:
    draft = client.post("/api/admin/songs", json={"title": "Hidden Draft", "slug": "hidden"}).json()
    ready = client.post(
        "/api/admin/songs",
        json={"title": "Visible Song", "artist": "Findable Artist", "slug": "visible"},
    ).json()
    uploaded = client.post(
        f"/api/admin/songs/{ready['id']}/stems/upload",
        data={"name": "Drums", "role": "drums"},
        files={"file": ("drums.wav", b"RIFF----WAVEfmt data", "audio/wav")},
    ).json()
    with client.session_factory() as db:  # type: ignore[attr-defined]
        song = db.get(Song, ready["id"])
        stem = db.get(Stem, uploaded["id"])
        assert song is not None and stem is not None
        song_key = db.query(SongKey).filter_by(song_id=ready["id"], semitone_offset=0).one()
        converted = Path(client.storage.key_asset_path(ready["id"], song_key.id, uploaded["id"]))  # type: ignore[attr-defined]
        converted.parent.mkdir(parents=True)
        converted.write_bytes(b"m4a")
        song.status = "ready"
        song.target_sample_rate = 48000
        song.target_duration_ms = 1000
        song_key.status = "ready"
        stem.status = "ready"
        stem.converted_path = str(converted)
        stem.codec = "aac-lc"
        stem.channels = 2
        stem.sample_rate = 48000
        stem.duration_ms = 1000
        stem.file_size_bytes = 3
        stem.bitrate_kbps = 160
        asset = StemKeyAsset(song_key_id=song_key.id, stem_id=stem.id)
        asset.status = "ready"
        asset.file_path = str(converted)
        asset.codec = "aac-lc"
        asset.channels = 2
        asset.sample_rate = 48000
        asset.duration_ms = 1000
        asset.file_size_bytes = 3
        asset.bitrate_kbps = 160
        db.add(asset)
        db.commit()

    search = client.get("/api/public/songs", params={"query": "visible"})
    assert search.status_code == 200
    assert [song["id"] for song in search.json()] == [ready["id"]]
    artist_search = client.get("/api/public/songs", params={"query": "Findable"})
    assert artist_search.status_code == 200
    assert [song["id"] for song in artist_search.json()] == [ready["id"]]
    assert client.get("/api/public/songs", params={"query": "hidden"}).json() == []
    assert client.get(f"/api/public/songs/{draft['id']}/manifest").status_code == 404

    manifest = client.get(f"/api/public/songs/{ready['id']}/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["playerSettings"]["stemGainDefaultDb"] == 0
