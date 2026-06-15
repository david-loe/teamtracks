from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.storage import StorageService, get_storage_service
from app.services.auth import require_admin_session


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    Base.metadata.create_all(bind=engine)

    storage = StorageService(storage_root=tmp_path / "storage", source_root=tmp_path / "imports")
    storage.storage_root.mkdir(parents=True)
    storage.source_root.mkdir(parents=True)

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
    app.dependency_overrides[require_admin_session] = lambda: None

    with TestClient(app) as test_client:
        test_client.storage = storage  # type: ignore[attr-defined]
        test_client.session_factory = TestingSessionLocal  # type: ignore[attr-defined]
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
