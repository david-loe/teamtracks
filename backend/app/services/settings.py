from sqlalchemy.orm import Session

from app.models.app_settings import AppSettings


def get_or_create_app_settings(db: Session) -> AppSettings:
    settings = db.get(AppSettings, 1)
    if settings is None:
        settings = AppSettings(id=1)
        db.add(settings)
        db.flush()
    return settings
