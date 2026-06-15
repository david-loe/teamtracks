"""create mvp tables

Revision ID: 0001_create_mvp_tables
Revises:
Create Date: 2026-06-11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_create_mvp_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "songs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("target_sample_rate", sa.Integer(), nullable=True),
        sa.Column("target_duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_songs_slug", "songs", ["slug"], unique=True)
    op.create_index("idx_songs_status", "songs", ["status"])

    op.create_table(
        "stems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("song_id", sa.Integer(), sa.ForeignKey("songs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=True),
        sa.Column("converted_path", sa.Text(), nullable=True),
        sa.Column("source_filename", sa.String(), nullable=True),
        sa.Column("source_format", sa.String(), nullable=False),
        sa.Column("codec", sa.String(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("channels", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("bitrate_kbps", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_stems_song_id", "stems", ["song_id"])
    op.create_index("idx_stems_status", "stems", ["status"])
    op.create_index("idx_stems_song_role", "stems", ["song_id", "role"])

    op.create_table(
        "conversion_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("song_id", sa.Integer(), sa.ForeignKey("songs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stem_id", sa.Integer(), sa.ForeignKey("stems.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("requested_by", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_jobs_status_created", "conversion_jobs", ["status", "created_at"])
    op.create_index("idx_jobs_song_id", "conversion_jobs", ["song_id"])
    op.create_index("idx_jobs_stem_id", "conversion_jobs", ["stem_id"])


def downgrade() -> None:
    op.drop_index("idx_jobs_stem_id", table_name="conversion_jobs")
    op.drop_index("idx_jobs_song_id", table_name="conversion_jobs")
    op.drop_index("idx_jobs_status_created", table_name="conversion_jobs")
    op.drop_table("conversion_jobs")
    op.drop_index("idx_stems_song_role", table_name="stems")
    op.drop_index("idx_stems_status", table_name="stems")
    op.drop_index("idx_stems_song_id", table_name="stems")
    op.drop_table("stems")
    op.drop_index("idx_songs_status", table_name="songs")
    op.drop_index("idx_songs_slug", table_name="songs")
    op.drop_table("songs")
