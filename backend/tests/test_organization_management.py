from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.organization import Organization
from app.models.song import Song
from app.services.passwords import verify_password


PNG_IMAGE = b"\x89PNG\r\n\x1a\nteamtracks-test-image"
JPEG_IMAGE = b"\xff\xd8\xff\xe0teamtracks-test-image"


def login_as_admin(client: TestClient, organization_id: int, user_password: str, admin_password: str) -> None:
    assert client.post(
        f"/api/organizations/{organization_id}/session",
        json={"password": user_password},
    ).status_code == 200
    assert client.post(
        f"/api/organizations/{organization_id}/admin/session",
        json={"password": admin_password},
    ).status_code == 200


def create_platform_organization(client: TestClient, name: str = "Platform Organization") -> dict:
    response = client.post(
        "/api/platform/organizations",
        data={
            "name": name,
            "userPassword": "platform-user-password",
            "adminPassword": "platform-admin-password",
        },
        files={"image": ("organization.png", PNG_IMAGE, "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_public_and_platform_organization_crud_with_images(client: TestClient) -> None:
    created = create_platform_organization(client)
    organization_id = created["id"]
    assert created["name"] == "Platform Organization"
    assert created["imageUrl"] == f"/api/organizations/{organization_id}/image"
    assert created["inviteUrl"].startswith("/invite/")

    public_organizations = client.get("/api/organizations")
    assert public_organizations.status_code == 200
    assert {item["id"] for item in public_organizations.json()} == {
        client.organization_id,  # type: ignore[attr-defined]
        organization_id,
    }

    image = client.get(created["imageUrl"])
    assert image.status_code == 200
    assert image.content == PNG_IMAGE
    assert image.headers["content-type"] == "image/png"

    updated = client.patch(
        f"/api/platform/organizations/{organization_id}",
        data={
            "name": "Renamed Organization",
            "userPassword": "updated-user-password",
            "adminPassword": "updated-admin-password",
        },
        files={"image": ("organization.jpg", JPEG_IMAGE, "image/jpeg")},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Renamed Organization"
    assert client.get(created["imageUrl"]).headers["content-type"] == "image/jpeg"

    with client.session_factory() as db:  # type: ignore[attr-defined]
        organization = db.get(Organization, organization_id)
        assert organization is not None
        assert verify_password(organization.user_password_hash, "updated-user-password")
        assert verify_password(organization.admin_password_hash, "updated-admin-password")
        assert organization.user_auth_version == 2
        assert organization.admin_auth_version == 2

    assert client.delete(f"/api/platform/organizations/{organization_id}").status_code == 204
    assert client.get(created["imageUrl"]).status_code == 404
    with client.session_factory() as db:  # type: ignore[attr-defined]
        assert db.get(Organization, organization_id) is None


def test_organization_image_validation(client: TestClient) -> None:
    invalid = client.post(
        "/api/platform/organizations",
        data={
            "name": "Invalid Image",
            "userPassword": "valid-user-password",
            "adminPassword": "valid-admin-password",
        },
        files={"image": ("fake.png", b"not-an-image", "image/png")},
    )
    assert invalid.status_code == 400

    too_large = client.post(
        "/api/platform/organizations",
        data={
            "name": "Large Image",
            "userPassword": "valid-user-password",
            "adminPassword": "valid-admin-password",
        },
        files={"image": ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024), "image/png")},
    )
    assert too_large.status_code == 413

    with client.session_factory() as db:  # type: ignore[attr-defined]
        names = {organization.name for organization in db.query(Organization).all()}
        assert "Invalid Image" not in names
        assert "Large Image" not in names


def test_admin_can_manage_metadata_and_rotate_passwords(client: TestClient) -> None:
    organization_id = client.organization_id  # type: ignore[attr-defined]
    login_as_admin(client, organization_id, "test-user-password", "test-admin-password")

    with TestClient(app) as other_browser:
        login_as_admin(other_browser, organization_id, "test-user-password", "test-admin-password")

        update_metadata = client.patch(
            f"/api/organizations/{organization_id}/admin/organization",
            data={"name": "Managed Organization"},
            files={"image": ("managed.png", PNG_IMAGE, "image/png")},
        )
        assert update_metadata.status_code == 200
        assert update_metadata.json()["name"] == "Managed Organization"

        user_password_change = client.put(
            f"/api/organizations/{organization_id}/admin/organization/user-password",
            json={"newPassword": "new-user-password"},
        )
        assert user_password_change.status_code == 204
        own_session = client.get("/api/session").json()
        assert own_session["authenticated"] is True
        assert own_session["organizations"][0]["isAdmin"] is True
        assert other_browser.get("/api/session").json() == {"authenticated": False, "organizations": []}

        assert other_browser.post(
            f"/api/organizations/{organization_id}/session",
            json={"password": "test-user-password"},
        ).status_code == 401
        assert other_browser.post(
            f"/api/organizations/{organization_id}/session",
            json={"password": "new-user-password"},
        ).status_code == 200
        assert other_browser.post(
            f"/api/organizations/{organization_id}/admin/session",
            json={"password": "test-admin-password"},
        ).status_code == 200

        wrong_current = client.put(
            f"/api/organizations/{organization_id}/admin/organization/admin-password",
            json={"currentPassword": "wrong", "newPassword": "new-admin-password"},
        )
        assert wrong_current.status_code == 401
        admin_password_change = client.put(
            f"/api/organizations/{organization_id}/admin/organization/admin-password",
            json={"currentPassword": "test-admin-password", "newPassword": "new-admin-password"},
        )
        assert admin_password_change.status_code == 204
        assert client.get("/api/session").json()["organizations"][0]["isAdmin"] is True
        assert other_browser.get("/api/session").json()["organizations"][0]["isAdmin"] is False


def test_invite_acceptance_and_regeneration(client: TestClient) -> None:
    organization_id = client.organization_id  # type: ignore[attr-defined]
    login_as_admin(client, organization_id, "test-user-password", "test-admin-password")
    details = client.get(f"/api/organizations/{organization_id}/admin/organization").json()
    old_token = details["inviteToken"]

    with TestClient(app) as invited_browser:
        first_accept = invited_browser.post(f"/api/invites/{old_token}/accept")
        assert first_accept.status_code == 200
        assert first_accept.json()["organizationId"] == organization_id
        assert first_accept.json()["session"]["organizations"][0]["id"] == organization_id
        assert invited_browser.post(f"/api/invites/{old_token}/accept").status_code == 200

        regenerated = client.post(
            f"/api/organizations/{organization_id}/admin/organization/invite/regenerate"
        )
        assert regenerated.status_code == 200
        new_token = regenerated.json()["inviteToken"]
        assert new_token != old_token
        assert invited_browser.get("/api/session").json()["authenticated"] is True

        with TestClient(app) as new_browser:
            assert new_browser.post(f"/api/invites/{old_token}/accept").status_code == 404
            assert new_browser.post(f"/api/invites/{new_token}/accept").status_code == 200
            assert new_browser.get("/api/session").json()["authenticated"] is True


def test_admin_deletion_removes_database_and_storage(client: TestClient) -> None:
    created = create_platform_organization(client, "Delete Organization")
    organization_id = created["id"]
    login_as_admin(
        client,
        organization_id,
        "platform-user-password",
        "platform-admin-password",
    )

    with client.session_factory() as db:  # type: ignore[attr-defined]
        song = Song(organization_id=organization_id, title="Delete Song", slug="delete-song")
        db.add(song)
        db.commit()
        db.refresh(song)
        song_id = song.id

    song_dir = Path(client.storage.song_dir(organization_id, song_id))  # type: ignore[attr-defined]
    song_dir.mkdir(parents=True)
    (song_dir / "test.bin").write_bytes(b"song")
    organization_dir = Path(client.storage.organization_dir(organization_id))  # type: ignore[attr-defined]
    assert organization_dir.is_dir()

    wrong_password = client.request(
        "DELETE",
        f"/api/organizations/{organization_id}/admin/organization",
        json={"adminPassword": "wrong-password"},
    )
    assert wrong_password.status_code == 401

    deleted = client.request(
        "DELETE",
        f"/api/organizations/{organization_id}/admin/organization",
        json={"adminPassword": "platform-admin-password"},
    )
    assert deleted.status_code == 204
    assert not song_dir.exists()
    assert not organization_dir.exists()
    with client.session_factory() as db:  # type: ignore[attr-defined]
        assert db.get(Organization, organization_id) is None
        assert db.get(Song, song_id) is None
