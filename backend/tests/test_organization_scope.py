from fastapi.testclient import TestClient

from app.models.app_settings import AppSettings
from app.models.conversion_job import ConversionJob
from app.models.organization import Organization
from app.models.song import Song
from app.models.song_key import SongKey
from app.models.stem import Stem
from app.services.passwords import hash_password


def test_all_content_endpoints_hide_foreign_organization_ids(client: TestClient) -> None:
    first_organization_id = client.organization_id  # type: ignore[attr-defined]
    with client.session_factory() as db:  # type: ignore[attr-defined]
        second_organization = Organization(
            name="Foreign Organization",
            image_path="organizations/foreign/image.png",
            user_password_hash=hash_password("foreign-user-password"),
            admin_password_hash=hash_password("foreign-admin-password"),
        )
        db.add(second_organization)
        db.flush()
        foreign_song = Song(
            organization_id=second_organization.id,
            title="Foreign Song",
            slug="shared-slug",
        )
        db.add(foreign_song)
        db.flush()
        foreign_key = SongKey(song_id=foreign_song.id, semitone_offset=0, is_original=True, status="draft")
        foreign_stem = Stem(song_id=foreign_song.id, name="Foreign Stem", role="other")
        db.add_all([foreign_key, foreign_stem])
        db.flush()
        foreign_job = ConversionJob(song_id=foreign_song.id, stem_id=foreign_stem.id)
        db.add(foreign_job)
        db.commit()
        second_organization_id = second_organization.id
        foreign_song_id = foreign_song.id
        foreign_key_id = foreign_key.id
        foreign_stem_id = foreign_stem.id
        foreign_job_id = foreign_job.id

    admin_base = f"/api/organizations/{first_organization_id}/admin"
    assert client.get(f"{admin_base}/songs/{foreign_song_id}").status_code == 404
    assert client.patch(
        f"{admin_base}/songs/{foreign_song_id}",
        json={"title": "Leaked", "slug": "leaked"},
    ).status_code == 404
    assert client.delete(f"{admin_base}/songs/{foreign_song_id}").status_code == 404
    assert client.get(f"{admin_base}/songs/{foreign_song_id}/stems").status_code == 404
    assert client.post(
        f"{admin_base}/songs/{foreign_song_id}/stems/upload",
        data={"name": "Foreign", "role": "other"},
        files={"file": ("foreign.wav", b"RIFF----WAVEfmt data", "audio/wav")},
    ).status_code == 404
    assert client.get(f"{admin_base}/songs/{foreign_song_id}/conversion-jobs").status_code == 404
    assert client.post(
        f"{admin_base}/songs/{foreign_song_id}/conversion-jobs",
        json={"stemIds": [foreign_stem_id]},
    ).status_code == 404
    assert client.get(f"{admin_base}/songs/{foreign_song_id}/manifest").status_code == 404
    assert client.get(f"{admin_base}/conversion-jobs/{foreign_job_id}").status_code == 404
    assert client.delete(f"{admin_base}/stems/{foreign_stem_id}").status_code == 404
    assert client.post(
        f"{admin_base}/songs/{foreign_song_id}/transpose",
        json={"targetKeys": [2]},
    ).status_code == 404
    assert client.get(f"{admin_base}/songs/{foreign_song_id}/key-assets").status_code == 404
    assert client.get(
        f"/media/organizations/{first_organization_id}/songs/{foreign_song_id}"
        f"/keys/{foreign_key_id}/stems/{foreign_stem_id}.m4a"
    ).status_code == 404
    assert client.get(f"/api/organizations/{first_organization_id}/songs").json() == []
    assert client.get(
        f"/api/organizations/{first_organization_id}/songs/{foreign_song_id}/manifest"
    ).status_code == 404
    assert client.get(f"/api/organizations/{second_organization_id}/songs").status_code == 401
    assert client.get(f"/api/organizations/{second_organization_id}/admin/settings").status_code == 401


def test_settings_and_storage_are_scoped_per_organization(client: TestClient) -> None:
    first_organization_id = client.organization_id  # type: ignore[attr-defined]
    with client.session_factory() as db:  # type: ignore[attr-defined]
        second_organization = Organization(
            name="Second Organization",
            image_path="organizations/second/image.png",
            user_password_hash=hash_password("second-user-password"),
            admin_password_hash=hash_password("second-admin-password"),
        )
        db.add(second_organization)
        db.flush()
        db.add(AppSettings(organization_id=second_organization.id, mono_bitrate_kbps=128))
        db.commit()
        second_organization_id = second_organization.id

    settings = client.get(f"/api/organizations/{first_organization_id}/admin/settings")
    assert settings.status_code == 200
    assert settings.json()["monoBitrateKbps"] == 96
    with client.session_factory() as db:  # type: ignore[attr-defined]
        assert db.get(AppSettings, second_organization_id).mono_bitrate_kbps == 128

    first_path = client.storage.key_asset_path(first_organization_id, 10, 20, 30)  # type: ignore[attr-defined]
    second_path = client.storage.key_asset_path(second_organization_id, 10, 20, 30)  # type: ignore[attr-defined]
    assert first_path != second_path
    assert f"organizations/{first_organization_id}/songs/10" in str(first_path)
    assert f"organizations/{second_organization_id}/songs/10" in str(second_path)


def test_legacy_global_content_routes_are_removed(client: TestClient) -> None:
    assert client.get("/api/songs").status_code == 404
    assert client.get("/api/admin/songs").status_code == 404
    assert client.get("/api/public/songs").status_code == 404
    assert client.get("/api/admin/settings").status_code == 404
    assert client.get("/api/admin/session").status_code == 404
