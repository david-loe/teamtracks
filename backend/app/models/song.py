from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain import SongStatus

if TYPE_CHECKING:
    from app.models.conversion_job import ConversionJob
    from app.models.organization import Organization
    from app.models.song_key import SongKey
    from app.models.stem import Stem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_songs_organization_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str] = mapped_column(String, nullable=False, default="")
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False, default=SongStatus.DRAFT.value, index=True)
    original_key: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_sample_rate: Mapped[int | None] = mapped_column(Integer)
    target_duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization: Mapped["Organization"] = relationship(back_populates="songs")
    stems: Mapped[list["Stem"]] = relationship(back_populates="song", cascade="all, delete-orphan")
    key_variants: Mapped[list["SongKey"]] = relationship(back_populates="song", cascade="all, delete-orphan")
    conversion_jobs: Mapped[list["ConversionJob"]] = relationship(back_populates="song", cascade="all, delete-orphan")
