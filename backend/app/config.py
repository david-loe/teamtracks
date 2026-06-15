from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TeamTracks"
    database_url: str = Field(default="sqlite:////data/db/teamtracks.db", validation_alias="DATABASE_URL")
    storage_root: Path = Field(default=Path("/data/storage"), validation_alias="STORAGE_ROOT")
    source_root: Path = Field(default=Path("/data/imports"), validation_alias="SOURCE_ROOT")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
