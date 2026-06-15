from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain import ConversionJobStatus
from app.models.song import utc_now

if TYPE_CHECKING:
    from app.models.song import Song
    from app.models.stem import Stem


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True)
    stem_id: Mapped[int | None] = mapped_column(ForeignKey("stems.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default=ConversionJobStatus.QUEUED.value, index=True)
    requested_by: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime | None] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    song: Mapped["Song"] = relationship(back_populates="conversion_jobs")
    stem: Mapped["Stem | None"] = relationship(back_populates="conversion_jobs")
