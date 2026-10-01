"""persisted content packs

Revision ID: 0006_content_packs
Revises: 0005_analytics_engine
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_content_packs"
down_revision = "0005_analytics_engine"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "content_packs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("team_profile_id", sa.Uuid(), sa.ForeignKey("team_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fixture_id", sa.Uuid(), sa.ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_job_id", sa.Uuid(), sa.ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NEEDS_REVIEW"),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("target_word_count", sa.Integer(), nullable=False),
        sa.Column("estimated_duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("emotion", _json_type(), nullable=False), sa.Column("narrative_angle", _json_type(), nullable=False),
        sa.Column("selected_insights", _json_type(), nullable=False), sa.Column("hooks", _json_type(), nullable=False),
        sa.Column("recommended_hook", sa.Text(), nullable=True), sa.Column("title", sa.String(length=240), nullable=True),
        sa.Column("first_screen_text", sa.String(length=240), nullable=True), sa.Column("script", sa.Text(), nullable=True),
        sa.Column("segments", _json_type(), nullable=False), sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("comment_question", sa.Text(), nullable=True), sa.Column("hashtags", _json_type(), nullable=False),
        sa.Column("evidence_manifest", _json_type(), nullable=False), sa.Column("quality_checks", _json_type(), nullable=False),
        sa.Column("quality_warning", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prompt_version", sa.String(length=80), nullable=False), sa.Column("llm_provider", sa.String(length=80), nullable=True),
        sa.Column("llm_model", sa.String(length=160), nullable=True), sa.Column("original_generated_payload", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("generation_job_id", name="uq_content_packs_generation_job"),
        sa.UniqueConstraint("fixture_id", "team_profile_id", "content_type", "revision_number", name="uq_content_packs_fixture_revision"),
    )
    op.create_index("ix_content_packs_team_profile_id", "content_packs", ["team_profile_id"])
    op.create_index("ix_content_packs_fixture_id", "content_packs", ["fixture_id"])
    op.create_index("ix_content_packs_content_type", "content_packs", ["content_type"])
    op.create_index("ix_content_packs_status", "content_packs", ["status"])


def downgrade() -> None:
    op.drop_table("content_packs")
