from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.song import utc_now

if TYPE_CHECKING:
    from app.models.organization import Organization


class BrowserSession(Base):
    __tablename__ = "browser_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    organization_accesses: Mapped[list["SessionOrganizationAccess"]] = relationship(
        back_populates="browser_session",
        cascade="all, delete-orphan",
    )


class SessionOrganizationAccess(Base):
    __tablename__ = "session_organization_accesses"
    __table_args__ = (
        UniqueConstraint(
            "browser_session_id",
            "organization_id",
            name="uq_session_organization_accesses_session_organization",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    browser_session_id: Mapped[int] = mapped_column(
        ForeignKey("browser_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_auth_version: Mapped[int] = mapped_column(Integer, nullable=False)
    admin_auth_version: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utc_now, onupdate=utc_now)

    browser_session: Mapped["BrowserSession"] = relationship(back_populates="organization_accesses")
    organization: Mapped["Organization"] = relationship(back_populates="session_accesses")
