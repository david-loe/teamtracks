from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain import StemStatus
from app.models.song import utc_now

if TYPE_CHECKING:
    from app.models.song_key import SongKey
    from app.models.stem import Stem


class StemKeyAsset(Base):
    __tablename__ = "stem_key_assets"
    __table_args__ = (UniqueConstraint("song_key_id", "stem_id", name="uq_stem_key_assets_key_stem"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_key_id: Mapped[int] = mapped_column(ForeignKey("song_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    stem_id: Mapped[int] = mapped_column(ForeignKey("stems.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=StemStatus.UPLOADED.value, index=True)
    file_path: Mapped[str | None] = mapped_column(Text)
    codec: Mapped[str | None] = mapped_column(String)
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    channels: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    bitrate_kbps: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    song_key: Mapped["SongKey"] = relationship(back_populates="stem_assets")
    stem: Mapped["Stem"] = relationship(back_populates="key_assets")
