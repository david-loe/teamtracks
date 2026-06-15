from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain import ConversionJobStatus, ConversionJobType


class ConversionJobCreate(BaseModel):
    stem_ids: list[int] | None = Field(default=None, alias="stemIds")
    requested_by: str | None = Field(default=None, alias="requestedBy")

    model_config = ConfigDict(populate_by_name=True)


class ConversionJobBatchRead(BaseModel):
    job_ids: list[int] = Field(alias="jobIds")
    status: ConversionJobStatus

    model_config = ConfigDict(populate_by_name=True)


class ConversionJobRead(BaseModel):
    id: int
    song_id: int = Field(alias="songId")
    stem_id: int | None = Field(default=None, alias="stemId")
    song_key_id: int | None = Field(default=None, alias="songKeyId")
    job_type: ConversionJobType = Field(alias="jobType")
    target_key: int | None = Field(default=None, alias="targetKey")
    semitone_offset: int | None = Field(default=None, alias="semitoneOffset")
    status: ConversionJobStatus
    requested_by: str | None = Field(default=None, alias="requestedBy")
    mono_bitrate_kbps: int = Field(alias="monoBitrateKbps")
    stereo_bitrate_kbps: int = Field(alias="stereoBitrateKbps")
    target_sample_rate: int = Field(alias="targetSampleRate")
    duration_tolerance_ms: int = Field(alias="durationToleranceMs")
    started_at: datetime | None = Field(default=None, alias="startedAt")
    finished_at: datetime | None = Field(default=None, alias="finishedAt")
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
