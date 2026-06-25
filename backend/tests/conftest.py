from collections.abc import Generator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.organization import Organization
from app.models.browser_session import BrowserSession, SessionOrganizationAccess
from app.services.passwords import hash_password
from app.services.login_rate_limit import reset_all_login_rate_limits
from app.services.storage import StorageService, get_storage_service
from app.services.auth import (
    BROWSER_SESSION_COOKIE_NAME,
    get_auth_now,
    hash_session_token,
)
from app.config import get_settings


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    reset_all_login_rate_limits()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    Base.metadata.create_all(bind=engine)
    test_session_token = "test-browser-session-token"
    with Session(engine) as db:
        organization = Organization(
            name="Test Organization",
            image_path="organizations/1/image.png",
            user_password_hash=hash_password("test-user-password"),
            admin_password_hash=hash_password("test-admin-password"),
        )
        db.add(organization)
        db.commit()
        db.refresh(organization)
        organization_id = organization.id
        browser_session = BrowserSession(
            token_hash=hash_session_token(test_session_token),
            expires_at=get_auth_now() + timedelta(days=730),
        )
        db.add(browser_session)
        db.flush()
        db.add(
            SessionOrganizationAccess(
                browser_session_id=browser_session.id,
                organization_id=organization_id,
                user_auth_version=organization.user_auth_version,
                admin_auth_version=organization.admin_auth_version,
            )
        )
        db.commit()

    storage = StorageService(storage_root=tmp_path / "storage")
    storage.storage_root.mkdir(parents=True)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_storage() -> StorageService:
        return storage

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = override_get_storage
    with TestClient(app) as test_client:
        test_client.cookies.set(BROWSER_SESSION_COOKIE_NAME, test_session_token)
        platform_login = test_client.post(
            "/api/platform/session",
            json={"password": get_settings().platform_admin_password.get_secret_value()},
        )
        assert platform_login.status_code == 200
        test_client.storage = storage  # type: ignore[attr-defined]
        test_client.session_factory = TestingSessionLocal  # type: ignore[attr-defined]
        test_client.organization_id = organization_id  # type: ignore[attr-defined]
        yield test_client

    app.dependency_overrides.clear()
    reset_all_login_rate_limits()
    Base.metadata.drop_all(bind=engine)
