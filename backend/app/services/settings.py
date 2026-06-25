from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings
def get_or_create_app_settings(db: Session, organization_id: int) -> AppSettings:
    settings = db.get(AppSettings, organization_id)
    if settings is None:
        settings = AppSettings(organization_id=organization_id)
        db.add(settings)
        db.flush()
    return settings
