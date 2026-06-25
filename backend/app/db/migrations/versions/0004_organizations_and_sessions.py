"""Add organizations, browser sessions, and organization-scoped data.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("image_path", sa.String(), nullable=False),
        sa.Column("user_password_hash", sa.String(), nullable=False),
        sa.Column("admin_password_hash", sa.String(), nullable=False),
        sa.Column("user_auth_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("admin_auth_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("invite_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "browser_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_browser_sessions_token_hash", "browser_sessions", ["token_hash"], unique=True)
    op.create_index("ix_browser_sessions_expires_at", "browser_sessions", ["expires_at"])

    op.create_table(
        "session_organization_accesses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "browser_session_id",
            sa.Integer(),
            sa.ForeignKey("browser_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_auth_version", sa.Integer(), nullable=False),
        sa.Column("admin_auth_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "browser_session_id",
            "organization_id",
            name="uq_session_organization_accesses_session_organization",
        ),
    )
    op.create_index(
        "ix_session_organization_accesses_browser_session_id",
        "session_organization_accesses",
        ["browser_session_id"],
    )
    op.create_index(
        "ix_session_organization_accesses_organization_id",
        "session_organization_accesses",
        ["organization_id"],
    )

    op.drop_table("app_settings")
    op.create_table(
        "app_settings",
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("mono_bitrate_kbps", sa.Integer(), nullable=False, server_default="96"),
        sa.Column("stereo_bitrate_kbps", sa.Integer(), nullable=False, server_default="160"),
        sa.Column("target_sample_rate", sa.Integer(), nullable=False, server_default="48000"),
        sa.Column("duration_tolerance_ms", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("stem_gain_default_db", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stem_gain_min_db", sa.Integer(), nullable=False, server_default="-24"),
        sa.Column("stem_gain_max_db", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("stem_gain_step_db", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("focus_gain_default_db", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("focus_gain_min_db", sa.Integer(), nullable=False, server_default="-12"),
        sa.Column("focus_gain_max_db", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("background_gain_default_db", sa.Integer(), nullable=False, server_default="-12"),
        sa.Column("background_gain_min_db", sa.Integer(), nullable=False, server_default="-24"),
        sa.Column("background_gain_max_db", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.drop_index("idx_songs_slug", table_name="songs")
    with op.batch_alter_table("songs") as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=False))
        batch_op.create_foreign_key(
            "fk_songs_organization_id_organizations",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_songs_organization_slug",
            ["organization_id", "slug"],
        )
    op.create_index("ix_songs_organization_id", "songs", ["organization_id"])
    op.create_index("ix_songs_slug", "songs", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_songs_slug", table_name="songs")
    op.drop_index("ix_songs_organization_id", table_name="songs")
    with op.batch_alter_table("songs") as batch_op:
        batch_op.drop_constraint("uq_songs_organization_slug", type_="unique")
        batch_op.drop_constraint("fk_songs_organization_id_organizations", type_="foreignkey")
        batch_op.drop_column("organization_id")
    op.create_index("idx_songs_slug", "songs", ["slug"], unique=True)

    op.drop_table("app_settings")
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mono_bitrate_kbps", sa.Integer(), nullable=False, server_default="96"),
        sa.Column("stereo_bitrate_kbps", sa.Integer(), nullable=False, server_default="160"),
        sa.Column("target_sample_rate", sa.Integer(), nullable=False, server_default="48000"),
        sa.Column("duration_tolerance_ms", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("stem_gain_default_db", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stem_gain_min_db", sa.Integer(), nullable=False, server_default="-24"),
        sa.Column("stem_gain_max_db", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("stem_gain_step_db", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("focus_gain_default_db", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("focus_gain_min_db", sa.Integer(), nullable=False, server_default="-12"),
        sa.Column("focus_gain_max_db", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("background_gain_default_db", sa.Integer(), nullable=False, server_default="-12"),
        sa.Column("background_gain_min_db", sa.Integer(), nullable=False, server_default="-24"),
        sa.Column("background_gain_max_db", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        """INSERT INTO app_settings (
        id, mono_bitrate_kbps, stereo_bitrate_kbps, target_sample_rate, duration_tolerance_ms,
        stem_gain_default_db, stem_gain_min_db, stem_gain_max_db, stem_gain_step_db,
        focus_gain_default_db, focus_gain_min_db, focus_gain_max_db,
        background_gain_default_db, background_gain_min_db, background_gain_max_db, updated_at
        ) VALUES (1, 96, 160, 48000, 100, 0, -24, 6, 1, 0, -12, 6, -12, -24, 0, CURRENT_TIMESTAMP)"""
    )

    op.drop_index(
        "ix_session_organization_accesses_organization_id",
        table_name="session_organization_accesses",
    )
    op.drop_index(
        "ix_session_organization_accesses_browser_session_id",
        table_name="session_organization_accesses",
    )
    op.drop_table("session_organization_accesses")
    op.drop_index("ix_browser_sessions_expires_at", table_name="browser_sessions")
    op.drop_index("ix_browser_sessions_token_hash", table_name="browser_sessions")
    op.drop_table("browser_sessions")
    op.drop_table("organizations")
