from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain import SongStatus
from app.models.song import utc_now

if TYPE_CHECKING:
    from app.models.song import Song
    from app.models.stem_key_asset import StemKeyAsset


class SongKey(Base):
    __tablename__ = "song_keys"
    __table_args__ = (UniqueConstraint("song_id", "semitone_offset", name="uq_song_keys_song_semitone_offset"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True)
    semitone_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    is_original: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=SongStatus.DRAFT.value, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    song: Mapped["Song"] = relationship(back_populates="key_variants")
    stem_assets: Mapped[list["StemKeyAsset"]] = relationship(back_populates="song_key", cascade="all, delete-orphan")
