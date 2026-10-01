"""metric registry and insight candidates

Revision ID: 0005_analytics_engine
Revises: 0004_statistics_history
Create Date: 2026-09-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_analytics_engine"
down_revision = "0004_statistics_history"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "metric_definitions",
        sa.Column("code", sa.String(length=80), primary_key=True),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("unit", sa.String(length=24), nullable=False),
        sa.Column("higher_is_better", sa.Boolean(), nullable=True),
        sa.Column(
            "importance_weight", sa.Float(), nullable=False, server_default="0.5"
        ),
        sa.Column("editorial_weight", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("default_anomaly_threshold", sa.Float(), nullable=False),
        sa.Column("metric_floor", sa.Float(), nullable=False, server_default="1"),
        sa.Column("min_sample_size", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("provider_mapping", _json_type(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_metric_definitions_scope", "metric_definitions", ["scope"])
    op.create_index("ix_metric_definitions_enabled", "metric_definitions", ["enabled"])

    op.create_table(
        "insight_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "fixture_id",
            sa.Uuid(),
            sa.ForeignKey("fixtures.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "team_profile_id",
            sa.Uuid(),
            sa.ForeignKey("team_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("calculation_key", sa.String(length=180), nullable=False),
        sa.Column("insight_type", sa.String(length=80), nullable=False),
        sa.Column("headline_internal", sa.String(length=240), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("evidence", _json_type(), nullable=False),
        sa.Column("baseline", _json_type(), nullable=False),
        sa.Column("metric_codes", _json_type(), nullable=False),
        sa.Column("deviation_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("context_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("novelty_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("final_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "direction", sa.String(length=16), nullable=False, server_default="NEUTRAL"
        ),
        sa.Column("eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rejection_reason", sa.String(length=80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "final_score BETWEEN 0 AND 100", name="ck_insight_candidates_final_score"
        ),
        sa.UniqueConstraint(
            "fixture_id",
            "team_profile_id",
            "content_type",
            "calculation_key",
            name="uq_insight_candidate_calculation",
        ),
    )
    op.create_index(
        "ix_insight_candidates_fixture_id", "insight_candidates", ["fixture_id"]
    )
    op.create_index(
        "ix_insight_candidates_team_profile_id",
        "insight_candidates",
        ["team_profile_id"],
    )
    op.create_index(
        "ix_insight_candidates_content_type", "insight_candidates", ["content_type"]
    )
    op.create_index(
        "ix_insight_candidates_insight_type", "insight_candidates", ["insight_type"]
    )
    op.create_index(
        "ix_insight_candidates_eligible", "insight_candidates", ["eligible"]
    )


def downgrade() -> None:
    op.drop_table("insight_candidates")
    op.drop_table("metric_definitions")
