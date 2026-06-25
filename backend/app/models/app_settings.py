from datetime import datetime

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.song import utc_now

if TYPE_CHECKING:
    from app.models.organization import Organization


class AppSettings(Base):
    __tablename__ = "app_settings"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mono_bitrate_kbps: Mapped[int] = mapped_column(Integer, nullable=False, default=96)
    stereo_bitrate_kbps: Mapped[int] = mapped_column(Integer, nullable=False, default=160)
    target_sample_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=48000)
    duration_tolerance_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    stem_gain_default_db: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stem_gain_min_db: Mapped[int] = mapped_column(Integer, nullable=False, default=-24)
    stem_gain_max_db: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    stem_gain_step_db: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    focus_gain_default_db: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    focus_gain_min_db: Mapped[int] = mapped_column(Integer, nullable=False, default=-12)
    focus_gain_max_db: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    background_gain_default_db: Mapped[int] = mapped_column(Integer, nullable=False, default=-12)
    background_gain_min_db: Mapped[int] = mapped_column(Integer, nullable=False, default=-24)
    background_gain_max_db: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    organization: Mapped["Organization"] = relationship(back_populates="app_settings")
