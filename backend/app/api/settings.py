from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import AppSettingsRead, AppSettingsUpdate
from app.services.auth import require_admin_session
from app.services.settings import get_or_create_app_settings


router = APIRouter(
    prefix="/api/admin/settings",
    tags=["admin-settings"],
    dependencies=[Depends(require_admin_session)],
)


@router.get("", response_model=AppSettingsRead)
def get_settings(db: Session = Depends(get_db)):
    settings = get_or_create_app_settings(db)
    db.commit()
    db.refresh(settings)
    return settings


@router.put("", response_model=AppSettingsRead)
def update_settings(payload: AppSettingsUpdate, db: Session = Depends(get_db)):
    settings = get_or_create_app_settings(db)
    for key, value in payload.model_dump().items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings
