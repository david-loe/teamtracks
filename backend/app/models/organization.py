from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.song import utc_now

if TYPE_CHECKING:
    from app.models.app_settings import AppSettings
    from app.models.browser_session import SessionOrganizationAccess
    from app.models.song import Song


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    image_path: Mapped[str] = mapped_column(String, nullable=False)
    user_password_hash: Mapped[str] = mapped_column(String, nullable=False)
    admin_password_hash: Mapped[str] = mapped_column(String, nullable=False)
    user_auth_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    admin_auth_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    invite_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    songs: Mapped[list["Song"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    app_settings: Mapped["AppSettings"] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
        uselist=False,
    )
    session_accesses: Mapped[list["SessionOrganizationAccess"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
