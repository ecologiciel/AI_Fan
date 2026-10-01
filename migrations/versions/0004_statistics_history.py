"""statistics history and deterministic baselines

Revision ID: 0004_statistics_history
Revises: 0003_generation_jobs
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_statistics_history"
down_revision = "0003_generation_jobs"
branch_labels = None
depends_on = None


def _uuid_type() -> sa.types.TypeEngine[object]:
    return sa.Uuid()


def _json_type() -> sa.types.TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "team_match_stats",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("fixture_id", _uuid_type(), sa.ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("team_external_id", sa.String(length=120), nullable=False),
        sa.Column("metric_code", sa.String(length=80), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("metric_unit", sa.String(length=24), nullable=False, server_default="count"),
        sa.Column("period", sa.String(length=24), nullable=False, server_default="ALL"),
        sa.Column("provider_type_id", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("fixture_id", "team_external_id", "metric_code", "period", name="uq_team_match_stat"),
    )
    op.create_index("ix_team_match_stats_fixture_id", "team_match_stats", ["fixture_id"])
    op.create_index("ix_team_match_stats_team_external_id", "team_match_stats", ["team_external_id"])
    op.create_index("ix_team_match_stats_metric_code", "team_match_stats", ["metric_code"])

    op.create_table(
        "player_match_stats",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("fixture_id", _uuid_type(), sa.ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_external_id", sa.String(length=120), nullable=False),
        sa.Column("player_name", sa.String(length=180), nullable=False),
        sa.Column("team_external_id", sa.String(length=120), nullable=True),
        sa.Column("minutes_played", sa.Float(), nullable=True),
        sa.Column("metric_code", sa.String(length=80), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("metric_unit", sa.String(length=24), nullable=False, server_default="count"),
        sa.Column("period", sa.String(length=24), nullable=False, server_default="ALL"),
        sa.Column("provider_type_id", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("fixture_id", "player_external_id", "metric_code", "period", name="uq_player_match_stat"),
    )
    op.create_index("ix_player_match_stats_fixture_id", "player_match_stats", ["fixture_id"])
    op.create_index("ix_player_match_stats_player_external_id", "player_match_stats", ["player_external_id"])
    op.create_index("ix_player_match_stats_team_external_id", "player_match_stats", ["team_external_id"])
    op.create_index("ix_player_match_stats_metric_code", "player_match_stats", ["metric_code"])

    op.create_table(
        "match_events",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("fixture_id", _uuid_type(), sa.ForeignKey("fixtures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_event_id", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=True),
        sa.Column("extra_minute", sa.Integer(), nullable=True),
        sa.Column("team_external_id", sa.String(length=120), nullable=True),
        sa.Column("player_external_id", sa.String(length=120), nullable=True),
        sa.Column("player_name", sa.String(length=180), nullable=True),
        sa.Column("payload", _json_type(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("fixture_id", "provider_event_id", name="uq_match_event_provider_id"),
    )
    op.create_index("ix_match_events_fixture_id", "match_events", ["fixture_id"])

    op.create_table(
        "baselines",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_external_id", sa.String(length=120), nullable=False),
        sa.Column("competition_id", _uuid_type(), sa.ForeignKey("competitions.id"), nullable=True),
        sa.Column("metric_code", sa.String(length=80), nullable=False),
        sa.Column("window_type", sa.String(length=48), nullable=False),
        sa.Column("window_size", sa.Integer(), nullable=False),
        sa.Column("context_key", sa.String(length=240), nullable=False),
        sa.Column("context", _json_type(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("mean_value", sa.Float(), nullable=True),
        sa.Column("median_value", sa.Float(), nullable=True),
        sa.Column("stddev_value", sa.Float(), nullable=True),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("entity_type", "entity_external_id", "competition_id", "metric_code", "window_type", "context_key", name="uq_baseline_context"),
    )
    op.create_index("ix_baselines_entity_type", "baselines", ["entity_type"])
    op.create_index("ix_baselines_entity_external_id", "baselines", ["entity_external_id"])
    op.create_index("ix_baselines_metric_code", "baselines", ["metric_code"])


def downgrade() -> None:
    op.drop_table("baselines")
    op.drop_table("match_events")
    op.drop_table("player_match_stats")
    op.drop_table("team_match_stats")
