from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.app_settings import AppSettings
from app.models.browser_session import BrowserSession, SessionOrganizationAccess
from app.models.organization import Organization
from app.models.song import Song
from app.services.passwords import hash_password, verify_password


def make_organization(name: str) -> Organization:
    return Organization(
        name=name,
        image_path=f"organizations/{name.lower()}/image.png",
        user_password_hash=hash_password(f"{name}-user-password"),
        admin_password_hash=hash_password(f"{name}-admin-password"),
    )


def test_organization_passwords_are_hashed_and_verifiable(client) -> None:
    with client.session_factory() as db:  # type: ignore[attr-defined]
        organization = db.get(Organization, client.organization_id)  # type: ignore[attr-defined]
        assert organization is not None
        assert organization.user_password_hash != "test-user-password"
        assert organization.admin_password_hash != "test-admin-password"
        assert verify_password(organization.user_password_hash, "test-user-password")
        assert verify_password(organization.admin_password_hash, "test-admin-password")
        assert not verify_password(organization.user_password_hash, "wrong-password")


def test_song_slugs_are_unique_per_organization(client) -> None:
    with client.session_factory() as db:  # type: ignore[attr-defined]
        second_organization = make_organization("Second")
        db.add(second_organization)
        db.flush()
        db.add_all(
            [
                Song(
                    organization_id=client.organization_id,  # type: ignore[attr-defined]
                    title="First",
                    slug="shared-slug",
                ),
                Song(
                    organization_id=second_organization.id,
                    title="Second",
                    slug="shared-slug",
                ),
            ]
        )
        db.commit()

        db.add(
            Song(
                organization_id=client.organization_id,  # type: ignore[attr-defined]
                title="Duplicate",
                slug="shared-slug",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_settings_and_session_access_are_organization_scoped(client) -> None:
    with client.session_factory() as db:  # type: ignore[attr-defined]
        second_organization = make_organization("Second")
        db.add(second_organization)
        db.flush()
        db.add_all(
            [
                AppSettings(organization_id=client.organization_id),  # type: ignore[attr-defined]
                AppSettings(organization_id=second_organization.id, mono_bitrate_kbps=128),
            ]
        )
        browser_session = BrowserSession(
            token_hash="a" * 64,
            expires_at=datetime.now(timezone.utc) + timedelta(days=730),
        )
        db.add(browser_session)
        db.flush()
        db.add_all(
            [
                SessionOrganizationAccess(
                    browser_session_id=browser_session.id,
                    organization_id=client.organization_id,  # type: ignore[attr-defined]
                    user_auth_version=1,
                    admin_auth_version=1,
                ),
                SessionOrganizationAccess(
                    browser_session_id=browser_session.id,
                    organization_id=second_organization.id,
                    user_auth_version=1,
                ),
            ]
        )
        db.commit()

        assert len(browser_session.organization_accesses) == 2
        assert {access.organization_id for access in browser_session.organization_accesses} == {
            client.organization_id,  # type: ignore[attr-defined]
            second_organization.id,
        }
