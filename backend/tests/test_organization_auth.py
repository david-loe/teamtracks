from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import ORGANIZATION_SESSION_MAX_AGE_SECONDS
from app.main import app
from app.models.browser_session import BrowserSession
from app.models.organization import Organization
from app.services.auth import BROWSER_SESSION_COOKIE_NAME, get_auth_now, hash_session_token
from app.services.passwords import hash_password


def create_organization(client: TestClient, name: str = "Second Organization") -> int:
    with client.session_factory() as db:  # type: ignore[attr-defined]
        organization = Organization(
            name=name,
            image_path=f"organizations/{name.lower().replace(' ', '-')}/image.png",
            user_password_hash=hash_password("second-user-password"),
            admin_password_hash=hash_password("second-admin-password"),
        )
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return organization.id


def test_browser_can_hold_multiple_organization_roles(client: TestClient) -> None:
    client.cookies.clear()
    second_organization_id = create_organization(client)
    first_organization_id = client.organization_id  # type: ignore[attr-defined]

    assert client.get("/api/session").json() == {"authenticated": False, "organizations": []}
    first_login = client.post(
        f"/api/organizations/{first_organization_id}/session",
        json={"password": "test-user-password"},
    )
    assert first_login.status_code == 200
    assert "HttpOnly" in first_login.headers["set-cookie"]
    assert f"Max-Age={ORGANIZATION_SESSION_MAX_AGE_SECONDS}" in first_login.headers["set-cookie"]
    assert first_login.json()["organizations"] == [
        {
            "id": first_organization_id,
            "name": "Test Organization",
            "imageUrl": f"/api/organizations/{first_organization_id}/image",
            "isAdmin": False,
        }
    ]

    assert client.post(
        f"/api/organizations/{second_organization_id}/admin/session",
        json={"password": "second-admin-password"},
    ).status_code == 401

    second_login = client.post(
        f"/api/organizations/{second_organization_id}/session",
        json={"password": "second-user-password"},
    )
    assert second_login.status_code == 200

    admin_login = client.post(
        f"/api/organizations/{first_organization_id}/admin/session",
        json={"password": "test-admin-password"},
    )
    assert admin_login.status_code == 200
    organizations = {item["id"]: item for item in admin_login.json()["organizations"]}
    assert organizations[first_organization_id]["isAdmin"] is True
    assert organizations[second_organization_id]["isAdmin"] is False

    assert client.delete(f"/api/organizations/{first_organization_id}/admin/session").status_code == 204
    organizations = {item["id"]: item for item in client.get("/api/session").json()["organizations"]}
    assert organizations[first_organization_id]["isAdmin"] is False

    assert client.delete(f"/api/organizations/{second_organization_id}/session").status_code == 204
    assert [item["id"] for item in client.get("/api/session").json()["organizations"]] == [
        first_organization_id
    ]

    assert client.delete("/api/session").status_code == 204
    assert client.get("/api/session").json() == {"authenticated": False, "organizations": []}


def test_auth_versions_revoke_only_the_matching_role(client: TestClient) -> None:
    client.cookies.clear()
    organization_id = client.organization_id  # type: ignore[attr-defined]
    assert client.post(
        f"/api/organizations/{organization_id}/session",
        json={"password": "test-user-password"},
    ).status_code == 200
    assert client.post(
        f"/api/organizations/{organization_id}/admin/session",
        json={"password": "test-admin-password"},
    ).status_code == 200

    with client.session_factory() as db:  # type: ignore[attr-defined]
        organization = db.get(Organization, organization_id)
        assert organization is not None
        organization.admin_auth_version += 1
        db.commit()

    session = client.get("/api/session").json()
    assert session["authenticated"] is True
    assert session["organizations"][0]["isAdmin"] is False

    with client.session_factory() as db:  # type: ignore[attr-defined]
        organization = db.get(Organization, organization_id)
        assert organization is not None
        organization.user_auth_version += 1
        db.commit()

    assert client.get("/api/session").json() == {"authenticated": False, "organizations": []}
    assert client.post(
        f"/api/organizations/{organization_id}/admin/session",
        json={"password": "test-admin-password"},
    ).status_code == 401


def test_session_expiration_and_sliding_renewal(client: TestClient) -> None:
    client.cookies.clear()
    initial_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    current_now = {"value": initial_now}
    app.dependency_overrides[get_auth_now] = lambda: current_now["value"]
    try:
        organization_id = client.organization_id  # type: ignore[attr-defined]
        login = client.post(
            f"/api/organizations/{organization_id}/session",
            json={"password": "test-user-password"},
        )
        assert login.status_code == 200
        raw_token = client.cookies.get(BROWSER_SESSION_COOKIE_NAME)
        assert raw_token is not None

        with client.session_factory() as db:  # type: ignore[attr-defined]
            browser_session = db.scalar(
                select(BrowserSession).where(BrowserSession.token_hash == hash_session_token(raw_token))
            )
            assert browser_session is not None
            assert _as_utc(browser_session.expires_at) == initial_now + timedelta(
                seconds=ORGANIZATION_SESSION_MAX_AGE_SECONDS
            )

        current_now["value"] = initial_now + timedelta(days=30)
        renewed = client.get("/api/session")
        assert renewed.status_code == 200
        assert f"Max-Age={ORGANIZATION_SESSION_MAX_AGE_SECONDS}" in renewed.headers["set-cookie"]
        with client.session_factory() as db:  # type: ignore[attr-defined]
            browser_session = db.scalar(
                select(BrowserSession).where(BrowserSession.token_hash == hash_session_token(raw_token))
            )
            assert browser_session is not None
            assert _as_utc(browser_session.expires_at) == current_now["value"] + timedelta(
                seconds=ORGANIZATION_SESSION_MAX_AGE_SECONDS
            )
            browser_session.expires_at = current_now["value"] - timedelta(seconds=1)
            db.commit()

        expired = client.get("/api/session")
        assert expired.status_code == 200
        assert expired.json() == {"authenticated": False, "organizations": []}
        with client.session_factory() as db:  # type: ignore[attr-defined]
            assert db.scalar(
                select(BrowserSession).where(BrowserSession.token_hash == hash_session_token(raw_token))
            ) is None
    finally:
        app.dependency_overrides.pop(get_auth_now, None)


def test_unknown_session_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.clear()
    client.cookies.set(BROWSER_SESSION_COOKIE_NAME, "manipulated-token")
    response = client.get("/api/session")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "organizations": []}
    assert f"{BROWSER_SESSION_COOKIE_NAME}=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_organization_login_rate_limit(client: TestClient) -> None:
    client.cookies.clear()
    organization_id = client.organization_id  # type: ignore[attr-defined]
    for _ in range(5):
        response = client.post(
            f"/api/organizations/{organization_id}/session",
            json={"password": "wrong-password"},
        )
        assert response.status_code == 401

    blocked = client.post(
        f"/api/organizations/{organization_id}/session",
        json={"password": "test-user-password"},
    )
    assert blocked.status_code == 429


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
