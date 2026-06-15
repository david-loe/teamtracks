from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TeamTracks"
    database_url: str = Field(default="sqlite:////data/db/teamtracks.db", validation_alias="DATABASE_URL")
    storage_root: Path = Field(default=Path("/data/storage"), validation_alias="STORAGE_ROOT")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    admin_password: SecretStr = Field(default=SecretStr("change-me"), validation_alias="ADMIN_PASSWORD")
    admin_session_secret: SecretStr = Field(
        default=SecretStr("development-session-secret-change-me"),
        validation_alias="ADMIN_SESSION_SECRET",
    )
    admin_session_hours: int = Field(default=12, validation_alias="ADMIN_SESSION_HOURS", ge=1, le=720)
    admin_cookie_secure: bool = Field(default=False, validation_alias="ADMIN_COOKIE_SECURE")
    stem_cache_max_age_seconds: int = Field(
        default=315_360_000,
        validation_alias="STEM_CACHE_MAX_AGE_SECONDS",
        ge=0,
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
