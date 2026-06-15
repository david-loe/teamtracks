"""Add song key variants and per-key stem assets.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("songs") as batch_op:
        batch_op.add_column(sa.Column("artist", sa.String(), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("original_key", sa.Integer(), nullable=False, server_default="0"))

    with op.batch_alter_table("stems") as batch_op:
        batch_op.add_column(sa.Column("key", sa.Integer(), nullable=True))

    op.create_table(
        "song_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("song_id", sa.Integer(), sa.ForeignKey("songs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("semitone_offset", sa.Integer(), nullable=False),
        sa.Column("is_original", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("song_id", "semitone_offset", name="uq_song_keys_song_semitone_offset"),
    )
    op.create_index("idx_song_keys_song_id", "song_keys", ["song_id"])
    op.create_index("idx_song_keys_status", "song_keys", ["status"])
    op.execute(
        """INSERT INTO song_keys (song_id, semitone_offset, is_original, status, error_message, created_at, updated_at)
        SELECT id, 0, 1, status, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM songs"""
    )

    op.create_table(
        "stem_key_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("song_key_id", sa.Integer(), sa.ForeignKey("song_keys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stem_id", sa.Integer(), sa.ForeignKey("stems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("codec", sa.String(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("channels", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("bitrate_kbps", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("song_key_id", "stem_id", name="uq_stem_key_assets_key_stem"),
    )
    op.create_index("idx_stem_key_assets_song_key_id", "stem_key_assets", ["song_key_id"])
    op.create_index("idx_stem_key_assets_stem_id", "stem_key_assets", ["stem_id"])
    op.create_index("idx_stem_key_assets_status", "stem_key_assets", ["status"])

    with op.batch_alter_table("conversion_jobs") as batch_op:
        batch_op.add_column(sa.Column("song_key_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("job_type", sa.String(), nullable=False, server_default="stem_conversion"))
        batch_op.add_column(sa.Column("target_key", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("semitone_offset", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_conversion_jobs_song_key_id_song_keys",
            "song_keys",
            ["song_key_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("idx_jobs_song_key_id", "conversion_jobs", ["song_key_id"])
    op.create_index("idx_jobs_job_type", "conversion_jobs", ["job_type"])


def downgrade() -> None:
    op.drop_index("idx_jobs_job_type", table_name="conversion_jobs")
    op.drop_index("idx_jobs_song_key_id", table_name="conversion_jobs")
    with op.batch_alter_table("conversion_jobs") as batch_op:
        batch_op.drop_constraint("fk_conversion_jobs_song_key_id_song_keys", type_="foreignkey")
        batch_op.drop_column("semitone_offset")
        batch_op.drop_column("target_key")
        batch_op.drop_column("job_type")
        batch_op.drop_column("song_key_id")
    op.drop_index("idx_stem_key_assets_status", table_name="stem_key_assets")
    op.drop_index("idx_stem_key_assets_stem_id", table_name="stem_key_assets")
    op.drop_index("idx_stem_key_assets_song_key_id", table_name="stem_key_assets")
    op.drop_table("stem_key_assets")
    op.drop_index("idx_song_keys_status", table_name="song_keys")
    op.drop_index("idx_song_keys_song_id", table_name="song_keys")
    op.drop_table("song_keys")
    with op.batch_alter_table("stems") as batch_op:
        batch_op.drop_column("key")
    with op.batch_alter_table("songs") as batch_op:
        batch_op.drop_column("original_key")
        batch_op.drop_column("artist")
