from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.domain import SongStatus, StemStatus
from app.main import app
from app.models.song import Song
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.models.stem_key_asset import StemKeyAsset


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
        song_key = db.query(SongKey).filter_by(song_id=song_id, semitone_offset=0).one_or_none()
        if song_key is None:
            song_key = SongKey(song_id=song_id, semitone_offset=0, is_original=True, status=SongStatus.READY.value)
            db.add(song_key)
            db.flush()
        song_key.status = SongStatus.READY.value
        asset = db.query(StemKeyAsset).filter_by(song_key_id=song_key.id, stem_id=stem_id).one_or_none()
        if asset is None:
            asset = StemKeyAsset(song_key_id=song_key.id, stem_id=stem_id)
            db.add(asset)
        asset.status = StemStatus.READY.value
        asset.file_path = str(converted_path)
        asset.codec = "aac-lc"
        asset.channels = 2
        asset.sample_rate = 48000
        asset.duration_ms = 184320
        asset.file_size_bytes = 2210340
        asset.bitrate_kbps = 160
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
        "artist": "",
        "slug": "manifest-song",
        "originalKey": 0,
        "durationMs": 184320,
        "sampleRate": 48000,
    }
    assert manifest["keyVariants"] == [
        {
            "id": manifest["selectedKeyId"],
            "semitoneOffset": 0,
            "isOriginal": True,
            "status": "ready",
            "playable": True,
            "errorMessage": None,
        }
    ]
    assert manifest["playable"] is True
    media_url = manifest["stems"][0]["url"]
    assert media_url.startswith(
        f"/media/songs/{song['id']}/keys/{manifest['selectedKeyId']}/stems/{ready_stem['id']}.m4a?v="
    )
    assert manifest["stems"] == [
        {
            "id": ready_stem["id"],
            "name": "drums",
            "role": "drums",
            "key": None,
            "focusable": True,
            "status": "ready",
            "url": media_url,
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


def test_partial_song_is_publicly_playable_with_ready_stem(client: TestClient) -> None:
    song = create_song(client)
    ready_stem = upload_stem(client, song["id"], name="drums", role="drums")
    pending_stem = upload_stem(client, song["id"], name="vocals", role="vocals")
    mark_stem_ready(client, song["id"], ready_stem["id"])

    with client.session_factory() as db:  # type: ignore[attr-defined]
        db.get(Song, song["id"]).status = SongStatus.DRAFT.value
        db.query(SongKey).filter_by(song_id=song["id"], is_original=True).one().status = SongStatus.DRAFT.value
        db.commit()

    list_response = client.get("/api/public/songs")
    assert list_response.status_code == 200
    listed_song = next(item for item in list_response.json() if item["id"] == song["id"])
    assert listed_song["status"] == "draft"
    assert listed_song["readyStemCount"] == 1
    assert listed_song["stemCount"] == 2

    response = client.get(f"/api/public/songs/{song['id']}/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["playable"] is True
    assert manifest["keyVariants"][0]["playable"] is True
    stems = {stem["id"]: stem for stem in manifest["stems"]}
    assert stems[ready_stem["id"]]["url"].startswith(
        f"/media/songs/{song['id']}/keys/{manifest['selectedKeyId']}/stems/{ready_stem['id']}.m4a?v="
    )
    assert stems[pending_stem["id"]]["status"] == "uploaded"
    assert stems[pending_stem["id"]]["url"] is None
    assert stems[pending_stem["id"]]["codec"] is None
    assert client.get(stems[ready_stem["id"]]["url"]).status_code == 200


def test_partial_key_variant_is_playable_and_empty_variant_is_not(client: TestClient) -> None:
    song = create_song(client)
    drums = upload_stem(client, song["id"], name="drums", role="drums")
    bass = upload_stem(client, song["id"], name="bass", role="bass")
    mark_stem_ready(client, song["id"], drums["id"])
    mark_stem_ready(client, song["id"], bass["id"])

    with client.session_factory() as db:  # type: ignore[attr-defined]
        db.get(Stem, drums["id"]).key = 0
        db.get(Stem, bass["id"]).key = 0
        original_key = db.query(SongKey).filter_by(song_id=song["id"], is_original=True).one()
        source_asset = db.query(StemKeyAsset).filter_by(song_key_id=original_key.id, stem_id=drums["id"]).one()
        partial_key = SongKey(song_id=song["id"], semitone_offset=2, is_original=False, status=SongStatus.DRAFT.value)
        empty_key = SongKey(song_id=song["id"], semitone_offset=4, is_original=False, status=SongStatus.DRAFT.value)
        db.add_all([partial_key, empty_key])
        db.flush()
        db.add(
            StemKeyAsset(
                song_key_id=partial_key.id,
                stem_id=drums["id"],
                status=StemStatus.READY.value,
                file_path=source_asset.file_path,
                codec=source_asset.codec,
                channels=source_asset.channels,
                sample_rate=source_asset.sample_rate,
                duration_ms=source_asset.duration_ms,
                file_size_bytes=source_asset.file_size_bytes,
                bitrate_kbps=source_asset.bitrate_kbps,
            )
        )
        db.commit()
        partial_key_id = partial_key.id
        empty_key_id = empty_key.id

    response = client.get(f"/api/public/songs/{song['id']}/manifest", params={"key": 2})
    assert response.status_code == 200
    manifest = response.json()
    variants = {variant["id"]: variant for variant in manifest["keyVariants"]}
    assert manifest["selectedKeyId"] == partial_key_id
    assert manifest["playable"] is True
    assert variants[partial_key_id]["status"] == "draft"
    assert variants[partial_key_id]["playable"] is True
    assert variants[empty_key_id]["playable"] is False

    stems = {stem["id"]: stem for stem in manifest["stems"]}
    assert stems[drums["id"]]["url"] is not None
    assert stems[bass["id"]]["url"] is None
    assert client.get(stems[drums["id"]]["url"]).status_code == 200
    compatibility_response = client.get(
        f"/api/public/songs/{song['id']}/manifest",
        params={"keyId": partial_key_id},
    )
    assert compatibility_response.status_code == 200
    assert compatibility_response.json()["selectedKeyId"] == partial_key_id

    unavailable_response = client.get(f"/api/public/songs/{song['id']}/manifest", params={"key": 4})
    assert unavailable_response.status_code == 404
    assert unavailable_response.json()["detail"] == "Tonart nicht verfügbar"

    missing_response = client.get(f"/api/public/songs/{song['id']}/manifest", params={"key": 6})
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Tonart nicht verfügbar"


def test_public_manifest_resolves_key_from_original_key_and_semitone_offset(client: TestClient) -> None:
    song = create_song(client)
    drums = upload_stem(client, song["id"], name="drums", role="drums")
    mark_stem_ready(client, song["id"], drums["id"])

    with client.session_factory() as db:  # type: ignore[attr-defined]
        db.get(Song, song["id"]).original_key = 9
        db.get(Stem, drums["id"]).key = 9
        original_key = db.query(SongKey).filter_by(song_id=song["id"], is_original=True).one()
        source_asset = db.query(StemKeyAsset).filter_by(song_key_id=original_key.id, stem_id=drums["id"]).one()
        target_key = SongKey(song_id=song["id"], semitone_offset=5, is_original=False, status=SongStatus.READY.value)
        db.add(target_key)
        db.flush()
        db.add(
            StemKeyAsset(
                song_key_id=target_key.id,
                stem_id=drums["id"],
                status=StemStatus.READY.value,
                file_path=source_asset.file_path,
                codec=source_asset.codec,
                channels=source_asset.channels,
                sample_rate=source_asset.sample_rate,
                duration_ms=source_asset.duration_ms,
                file_size_bytes=source_asset.file_size_bytes,
                bitrate_kbps=source_asset.bitrate_kbps,
            )
        )
        db.commit()
        target_key_id = target_key.id

    response = client.get(f"/api/public/songs/{song['id']}/manifest", params={"key": 2})

    assert response.status_code == 200
    assert response.json()["selectedKeyId"] == target_key_id


def test_public_manifest_rejects_key_and_key_id_together(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"])
    mark_stem_ready(client, song["id"], stem["id"])
    manifest = client.get(f"/api/public/songs/{song['id']}/manifest").json()

    response = client.get(
        f"/api/public/songs/{song['id']}/manifest",
        params={"key": 0, "keyId": manifest["selectedKeyId"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "key and keyId cannot be used together"


def test_public_manifest_validates_musical_key_range(client: TestClient) -> None:
    song = create_song(client)

    assert client.get(f"/api/public/songs/{song['id']}/manifest", params={"key": "x"}).status_code == 422
    assert client.get(f"/api/public/songs/{song['id']}/manifest", params={"key": 12}).status_code == 422


def test_keyless_stem_uses_original_asset_for_every_existing_key(client: TestClient) -> None:
    song = create_song(client)
    drums = upload_stem(client, song["id"], name="drums", role="drums")
    mark_stem_ready(client, song["id"], drums["id"])

    with client.session_factory() as db:  # type: ignore[attr-defined]
        original_key = db.query(SongKey).filter_by(song_id=song["id"], is_original=True).one()
        target_key = SongKey(song_id=song["id"], semitone_offset=2, is_original=False, status=SongStatus.DRAFT.value)
        db.add(target_key)
        db.flush()
        db.add(
            StemKeyAsset(
                song_key_id=target_key.id,
                stem_id=drums["id"],
                status=StemStatus.ERROR.value,
                error_message="stale duplicate",
            )
        )
        db.commit()
        original_key_id = original_key.id
        target_key_id = target_key.id

    response = client.get(f"/api/public/songs/{song['id']}/manifest", params={"keyId": target_key_id})
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["playable"] is True
    assert manifest["stems"][0]["status"] == "ready"
    assert manifest["stems"][0]["errorMessage"] is None
    assert manifest["stems"][0]["url"].startswith(
        f"/media/songs/{song['id']}/keys/{original_key_id}/stems/{drums['id']}.m4a?v="
    )
    assert client.get(manifest["stems"][0]["url"]).status_code == 200

    inventory = client.get(f"/api/admin/songs/{song['id']}/key-assets").json()
    assert inventory[0]["variants"] == []


def test_media_serves_ready_m4a_with_headers(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"])
    mark_stem_ready(client, song["id"], stem["id"])

    manifest = client.get(f"/api/songs/{song['id']}/manifest").json()
    url = manifest["stems"][0]["url"]
    response = client.get(url)
    assert response.status_code == 200
    assert response.content == b"m4a-data"
    assert response.headers["content-type"].startswith("audio/mp4")
    assert response.headers["cache-control"] == "public, max-age=315360000, immutable"
    assert response.headers["accept-ranges"] == "bytes"

    range_response = client.get(url, headers={"Range": "bytes=0-2"})
    assert range_response.status_code == 206
    assert range_response.content == b"m4a"
    assert range_response.headers["content-range"] == "bytes 0-2/8"


def test_media_cache_max_age_can_be_configured(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"])
    mark_stem_ready(client, song["id"], stem["id"])
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        STEM_CACHE_MAX_AGE_SECONDS=60,
    )

    manifest = client.get(f"/api/songs/{song['id']}/manifest").json()
    response = client.get(manifest["stems"][0]["url"])

    assert response.headers["cache-control"] == "public, max-age=60, immutable"


def test_manifest_media_url_changes_when_asset_is_updated(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"])
    mark_stem_ready(client, song["id"], stem["id"])

    manifest_url = f"/api/songs/{song['id']}/manifest"
    first_url = client.get(manifest_url).json()["stems"][0]["url"]
    assert client.get(manifest_url).json()["stems"][0]["url"] == first_url

    session_factory = client.session_factory  # type: ignore[attr-defined]
    with session_factory() as db:
        asset = db.query(StemKeyAsset).filter_by(stem_id=stem["id"]).one()
        asset.updated_at += timedelta(microseconds=1)
        db.commit()

    second_url = client.get(manifest_url).json()["stems"][0]["url"]
    assert second_url != first_url
    assert second_url.split("?", maxsplit=1)[0] == first_url.split("?", maxsplit=1)[0]


def test_media_rejects_missing_and_not_ready_files(client: TestClient) -> None:
    song = create_song(client)
    stem = upload_stem(client, song["id"])

    not_ready_response = client.get(f"/media/songs/{song['id']}/keys/999/stems/{stem['id']}.m4a")
    assert not_ready_response.status_code == 404

    mark_stem_ready(client, song["id"], stem["id"], write_file=False)
    manifest = client.get(f"/api/songs/{song['id']}/manifest").json()
    missing_file_response = client.get(f"/media/songs/{song['id']}/keys/{manifest['selectedKeyId']}/stems/{stem['id']}.m4a")
    assert missing_file_response.status_code == 404

    wrong_song_response = client.get(f"/media/songs/{song['id'] + 1}/keys/{manifest['selectedKeyId']}/stems/{stem['id']}.m4a")
    assert wrong_song_response.status_code == 404
