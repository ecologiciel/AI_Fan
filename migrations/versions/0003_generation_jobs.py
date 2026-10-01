"""Add persistent and idempotent generation jobs.

Revision ID: 0003_generation_jobs
Revises: 0002_team_profiles
Create Date: 2026-09-25 00:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_generation_jobs"
down_revision = "0002_team_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_profile_id", sa.Uuid(), nullable=False),
        sa.Column("fixture_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("idempotency_key", sa.String(length=300), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_profile_id"], ["team_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_generation_jobs_idempotency_key"),
    )
    op.create_index("ix_generation_jobs_fixture_id", "generation_jobs", ["fixture_id"])
    op.create_index("ix_generation_jobs_scheduled_for", "generation_jobs", ["scheduled_for"])
    op.create_index("ix_generation_jobs_status", "generation_jobs", ["status"])
    op.create_index("ix_generation_jobs_team_profile_id", "generation_jobs", ["team_profile_id"])
    op.create_index(
        "ix_generation_jobs_status_scheduled_for",
        "generation_jobs",
        ["status", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_status_scheduled_for", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_team_profile_id", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_status", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_scheduled_for", table_name="generation_jobs")
    op.drop_index("ix_generation_jobs_fixture_id", table_name="generation_jobs")
    op.drop_table("generation_jobs")
