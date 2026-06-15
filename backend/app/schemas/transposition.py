from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.domain import SongStatus, StemRole, StemStatus


class TransposeSongRequest(BaseModel):
    target_keys: list[Annotated[int, Field(ge=0, le=11)]] = Field(alias="targetKeys", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class SongKeyRead(BaseModel):
    id: int
    song_id: int = Field(alias="songId")
    semitone_offset: int = Field(ge=0, le=11, alias="semitoneOffset")
    is_original: bool = Field(alias="isOriginal")
    status: SongStatus
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class StemKeyAssetVariantRead(BaseModel):
    song_key_id: int = Field(alias="songKeyId")
    semitone_offset: int = Field(alias="semitoneOffset")
    target_key: int = Field(alias="targetKey")
    status: StemStatus | SongStatus
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = ConfigDict(populate_by_name=True)


class StemKeyAssetInventoryItemRead(BaseModel):
    stem_id: int = Field(alias="stemId")
    stem_name: str = Field(alias="stemName")
    stem_role: StemRole = Field(alias="stemRole")
    variants: list[StemKeyAssetVariantRead]

    model_config = ConfigDict(populate_by_name=True)
