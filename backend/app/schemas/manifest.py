from pydantic import BaseModel, ConfigDict, Field

from app.domain import SongStatus, StemRole, StemStatus
from app.schemas.settings import PlayerSettings


class ManifestSong(BaseModel):
    id: int
    title: str
    artist: str
    slug: str
    original_key: int = Field(alias="originalKey")
    duration_ms: int | None = Field(default=None, alias="durationMs")
    sample_rate: int | None = Field(default=None, alias="sampleRate")

    model_config = ConfigDict(populate_by_name=True)


class ManifestKeyVariant(BaseModel):
    id: int
    semitone_offset: int = Field(alias="semitoneOffset")
    is_original: bool = Field(alias="isOriginal")
    status: SongStatus
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = ConfigDict(populate_by_name=True)


class ManifestStem(BaseModel):
    id: int
    name: str
    role: StemRole
    key: int | None = None
    focusable: bool
    status: StemStatus
    url: str | None = None
    codec: str | None = None
    container: str | None = None
    channels: int | None = None
    sample_rate: int | None = Field(default=None, alias="sampleRate")
    duration_ms: int | None = Field(default=None, alias="durationMs")
    file_size_bytes: int | None = Field(default=None, alias="fileSizeBytes")
    bitrate_kbps: int | None = Field(default=None, alias="bitrateKbps")
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = ConfigDict(populate_by_name=True)


class SongManifest(BaseModel):
    song: ManifestSong
    key_variants: list[ManifestKeyVariant] = Field(alias="keyVariants")
    selected_key_id: int | None = Field(default=None, alias="selectedKeyId")
    playable: bool
    stems: list[ManifestStem]
    player_settings: PlayerSettings = Field(alias="playerSettings")

    model_config = ConfigDict(populate_by_name=True)
