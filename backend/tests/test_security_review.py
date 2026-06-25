import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from fastapi import Response
from fastapi.testclient import TestClient

from app.main import app
from app.models.stem import Stem
from app.services.auth import (
    create_browser_session,
    hash_session_token,
    require_organization_admin_access,
    require_platform_admin_session,
    require_user_access,
)
from app.config import get_settings
from app.services.invites import create_invite_token, parse_invite_token
from app.services.storage import StorageService


FORBIDDEN_RESPONSE_KEYS = {
    "userPasswordHash",
    "adminPasswordHash",
    "userAuthVersion",
    "adminAuthVersion",
    "inviteVersion",
    "imagePath",
    "tokenHash",
}


def test_api_responses_do_not_expose_auth_or_storage_fields(client: TestClient) -> None:
    responses = [
        client.get("/api/organizations").json(),
        client.get("/api/session").json(),
        client.get("/api/platform/organizations").json(),
        client.get(
            f"/api/organizations/{client.organization_id}/admin/organization"  # type: ignore[attr-defined]
        ).json(),
    ]

    for payload in responses:
        assert FORBIDDEN_RESPONSE_KEYS.isdisjoint(_all_keys(payload))


def test_openapi_admin_routes_have_server_side_authorization_dependencies() -> None:
    openapi_paths = set(app.openapi()["paths"])
    protected_routes = [
        route
        for route in _walk_routes(app.routes)
        if isinstance(route, APIRoute)
        and (
            route.path.startswith("/api/platform/organizations")
            or "/admin/" in route.path
        )
    ]

    assert protected_routes
    for route in protected_routes:
        assert route.path in openapi_paths
        dependencies = _dependency_calls(route.dependant)
        if route.path.startswith("/api/platform/organizations"):
            assert require_platform_admin_session in dependencies, route.path
        elif route.path.endswith("/admin/session"):
            assert require_user_access in dependencies, route.path
        else:
            assert require_organization_admin_access in dependencies, route.path


def test_platform_and_organization_admin_authorization_are_independent(client: TestClient) -> None:
    with TestClient(app) as browser:
        organization_id = client.organization_id  # type: ignore[attr-defined]
        assert browser.get("/api/platform/organizations").status_code == 401
        assert browser.get(f"/api/organizations/{organization_id}/admin/organization").status_code == 401

        assert browser.post(
            f"/api/organizations/{organization_id}/session",
            json={"password": "test-user-password"},
        ).status_code == 200
        assert browser.get(f"/api/organizations/{organization_id}/admin/organization").status_code == 403
        assert browser.get("/api/platform/organizations").status_code == 401


def test_upload_filenames_cannot_escape_organization_storage(client: TestClient) -> None:
    organization_id = client.organization_id  # type: ignore[attr-defined]
    song = client.post(
        f"/api/organizations/{organization_id}/admin/songs",
        json={"title": "Traversal", "slug": "traversal"},
    ).json()
    uploaded = client.post(
        f"/api/organizations/{organization_id}/admin/songs/{song['id']}/stems/upload",
        data={"name": "Traversal", "role": "other"},
        files={"file": ("../../outside.wav", b"RIFF----WAVEfmt data", "audio/wav")},
    )
    assert uploaded.status_code == 201

    with client.session_factory() as db:  # type: ignore[attr-defined]
        stem = db.get(Stem, uploaded.json()["id"])
        assert stem is not None
        assert stem.source_path is not None
        source_path = Path(stem.source_path)
    assert client.storage.is_inside_storage(source_path)  # type: ignore[attr-defined]
    assert source_path == client.storage.source_path(  # type: ignore[attr-defined]
        organization_id,
        song["id"],
        uploaded.json()["id"],
    )
    assert not (client.storage.storage_root.parent / "outside.wav").exists()  # type: ignore[attr-defined]


def test_storage_cleanup_refuses_paths_outside_the_storage_root(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"keep")
    storage = StorageService(storage_root)

    storage._unlink_if_inside_storage(outside)

    assert outside.read_bytes() == b"keep"


def test_session_entropy_and_invite_signature_strength(client: TestClient, monkeypatch) -> None:
    generated_token = "s" * 64
    requested_entropy_bytes: list[int] = []

    def fake_token_urlsafe(byte_count: int) -> str:
        requested_entropy_bytes.append(byte_count)
        return generated_token

    monkeypatch.setattr("app.services.auth.secrets.token_urlsafe", fake_token_urlsafe)
    with client.session_factory() as db:  # type: ignore[attr-defined]
        context = create_browser_session(
            db,
            Response(),
            get_settings(),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        assert requested_entropy_bytes == [48]
        assert context.session.token_hash == hash_session_token(generated_token)
        assert context.session.token_hash != generated_token
        assert len(context.session.token_hash) == 64
        db.rollback()

    invite = create_invite_token(client.organization_id, 1, get_settings())  # type: ignore[attr-defined]
    _payload, signature = invite.split(".", 1)
    decoded_signature = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
    assert len(decoded_signature) == 32
    assert parse_invite_token(invite, get_settings()) == (client.organization_id, 1)  # type: ignore[attr-defined]
    assert parse_invite_token(f"{invite[:-1]}x", get_settings()) is None


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _all_keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _all_keys(item)}
    return set()


def _dependency_calls(dependant: Any) -> set[Any]:
    calls = {dependant.call} if dependant.call is not None else set()
    for child in dependant.dependencies:
        calls.update(_dependency_calls(child))
    return calls


def _walk_routes(routes: list[Any]):
    for route in routes:
        nested_routes = getattr(route, "routes", None)
        if nested_routes is None:
            nested_routes = getattr(getattr(route, "original_router", None), "routes", None)
        if nested_routes is not None:
            yield from _walk_routes(nested_routes)
        else:
            yield route
