from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain import SongStatus


class SongCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    artist: str = Field(default="", max_length=200)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = None
    original_key: int = Field(default=0, ge=0, le=11, alias="originalKey")

    model_config = ConfigDict(populate_by_name=True)


class SongUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    artist: str | None = Field(default=None, max_length=200)
    original_key: int | None = Field(default=None, ge=0, le=11, alias="originalKey")

    model_config = ConfigDict(populate_by_name=True)


class SongRead(BaseModel):
    id: int
    title: str
    artist: str
    slug: str
    description: str | None = None
    status: SongStatus
    original_key: int = Field(alias="originalKey")
    target_sample_rate: int | None = Field(default=None, alias="targetSampleRate")
    target_duration_ms: int | None = Field(default=None, alias="targetDurationMs")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SongListItem(BaseModel):
    id: int
    title: str
    artist: str
    slug: str
    status: SongStatus
    original_key: int = Field(alias="originalKey")
    stem_count: int = Field(alias="stemCount")
    ready_stem_count: int = Field(alias="readyStemCount")
    duration_ms: int | None = Field(default=None, alias="durationMs")

    model_config = ConfigDict(populate_by_name=True)
