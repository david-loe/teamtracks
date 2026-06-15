"""Add application settings and conversion snapshots.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0002"
down_revision: str | None = "0001_create_mvp_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """INSERT INTO app_settings (
        id, mono_bitrate_kbps, stereo_bitrate_kbps, target_sample_rate, duration_tolerance_ms,
        stem_gain_default_db, stem_gain_min_db, stem_gain_max_db, stem_gain_step_db,
        focus_gain_default_db, focus_gain_min_db, focus_gain_max_db,
        background_gain_default_db, background_gain_min_db, background_gain_max_db, updated_at
        ) VALUES (1, 96, 160, 48000, 100, 0, -24, 6, 1, 0, -12, 6, -12, -24, 0, CURRENT_TIMESTAMP)"""
    )
    with op.batch_alter_table("conversion_jobs") as batch_op:
        batch_op.add_column(sa.Column("mono_bitrate_kbps", sa.Integer(), nullable=False, server_default="96"))
        batch_op.add_column(sa.Column("stereo_bitrate_kbps", sa.Integer(), nullable=False, server_default="160"))
        batch_op.add_column(sa.Column("target_sample_rate", sa.Integer(), nullable=False, server_default="48000"))
        batch_op.add_column(sa.Column("duration_tolerance_ms", sa.Integer(), nullable=False, server_default="100"))


def downgrade() -> None:
    with op.batch_alter_table("conversion_jobs") as batch_op:
        batch_op.drop_column("duration_tolerance_ms")
        batch_op.drop_column("target_sample_rate")
        batch_op.drop_column("stereo_bitrate_kbps")
        batch_op.drop_column("mono_bitrate_kbps")
    op.drop_table("app_settings")
