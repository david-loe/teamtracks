from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain import ConversionJobStatus, ConversionJobType
from app.models.song import utc_now

if TYPE_CHECKING:
    from app.models.song import Song
    from app.models.song_key import SongKey
    from app.models.stem import Stem


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True)
    stem_id: Mapped[int | None] = mapped_column(ForeignKey("stems.id", ondelete="CASCADE"), index=True)
    song_key_id: Mapped[int | None] = mapped_column(ForeignKey("song_keys.id", ondelete="SET NULL"), index=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False, default=ConversionJobType.STEM_CONVERSION.value, index=True)
    target_key: Mapped[int | None] = mapped_column(Integer)
    semitone_offset: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, nullable=False, default=ConversionJobStatus.QUEUED.value, index=True)
    requested_by: Mapped[str | None] = mapped_column(String)
    mono_bitrate_kbps: Mapped[int] = mapped_column(Integer, nullable=False, default=96)
    stereo_bitrate_kbps: Mapped[int] = mapped_column(Integer, nullable=False, default=160)
    target_sample_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=48000)
    duration_tolerance_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    started_at: Mapped[datetime | None] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    song: Mapped["Song"] = relationship(back_populates="conversion_jobs")
    stem: Mapped["Stem | None"] = relationship(back_populates="conversion_jobs")
    song_key: Mapped["SongKey | None"] = relationship()
