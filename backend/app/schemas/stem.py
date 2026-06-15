from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain import StemRole, StemStatus


class StemImport(BaseModel):
    source_path: str = Field(alias="sourcePath")
    name: str = Field(min_length=1, max_length=200)
    role: StemRole
    key: int | None = Field(default=None, ge=0, le=11)

    model_config = ConfigDict(populate_by_name=True)


class StemRead(BaseModel):
    id: int
    song_id: int = Field(alias="songId")
    name: str
    role: StemRole
    key: int | None = None
    status: StemStatus
    source_filename: str | None = Field(default=None, alias="sourceFilename")
    source_format: str = Field(alias="sourceFormat")
    codec: str | None = None
    sample_rate: int | None = Field(default=None, alias="sampleRate")
    channels: int | None = None
    duration_ms: int | None = Field(default=None, alias="durationMs")
    file_size_bytes: int | None = Field(default=None, alias="fileSizeBytes")
    bitrate_kbps: int | None = Field(default=None, alias="bitrateKbps")
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
