"""Create the multi-team profile domain.

Revision ID: 0002_team_profiles
Revises: 0001_bootstrap
Create Date: 2026-09-24 00:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_team_profiles"
down_revision = "0001_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("short_name", sa.String(length=80), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("football_provider", sa.String(length=80), nullable=False, server_default="sportmonks"),
        sa.Column("external_team_id", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=False, server_default="UTC"),
        sa.Column("primary_script_language", sa.String(length=16), nullable=False),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("cultural_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fan_identity", sa.String(length=240), nullable=False),
        sa.Column("character_name", sa.String(length=120), nullable=True),
        sa.Column("character_description", sa.Text(), nullable=True),
        sa.Column("speech_style", sa.Text(), nullable=True),
        sa.Column("speech_rate_wpm", sa.Integer(), nullable=False, server_default="150"),
        sa.Column("default_duration_mode", sa.String(length=16), nullable=False, server_default="AUTO"),
        sa.Column("forced_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("prematch_offset_minutes", sa.Integer(), nullable=False, server_default="360"),
        sa.Column("postmatch_delay_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("validation_mode", sa.String(length=32), nullable=False, server_default="HUMAN_REQUIRED"),
        sa.Column("emotion_base_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("provocation_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("humor_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("technical_depth", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("rivalry_boost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("optimism_bias", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("self_criticism_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("allowed_slang", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("forbidden_phrases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("favorite_expressions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("editorial_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("emotion_base_level BETWEEN 0 AND 100", name="ck_team_profiles_emotion"),
        sa.CheckConstraint("provocation_level BETWEEN 0 AND 100", name="ck_team_profiles_provocation"),
        sa.CheckConstraint("humor_level BETWEEN 0 AND 100", name="ck_team_profiles_humor"),
        sa.CheckConstraint("technical_depth BETWEEN 0 AND 100", name="ck_team_profiles_technical_depth"),
        sa.CheckConstraint("rivalry_boost BETWEEN 0 AND 100", name="ck_team_profiles_rivalry_boost"),
        sa.CheckConstraint("optimism_bias BETWEEN 0 AND 100", name="ck_team_profiles_optimism"),
        sa.CheckConstraint("self_criticism_level BETWEEN 0 AND 100", name="ck_team_profiles_self_criticism"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_team_profiles_slug", "team_profiles", ["slug"], unique=False)
    op.create_table(
        "competitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("external_competition_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_competition_id", name="uq_competitions_provider_external"),
    )
    op.create_table(
        "team_rivalries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_profile_id", sa.Uuid(), nullable=False),
        sa.Column("opponent_external_team_id", sa.String(length=120), nullable=False),
        sa.Column("opponent_name", sa.String(length=160), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("rivalry_label", sa.String(length=160), nullable=True),
        sa.Column("custom_character_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint("intensity BETWEEN 0 AND 100", name="ck_team_rivalries_intensity"),
        sa.ForeignKeyConstraint(["team_profile_id"], ["team_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_profile_id", "opponent_external_team_id", name="uq_team_rivalries_opponent"),
    )
    op.create_table(
        "team_competitions",
        sa.Column("team_profile_id", sa.Uuid(), nullable=False),
        sa.Column("competition_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_profile_id"], ["team_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("team_profile_id", "competition_id"),
    )
    op.create_table(
        "fixtures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("external_fixture_id", sa.String(length=120), nullable=False),
        sa.Column("competition_id", sa.Uuid(), nullable=True),
        sa.Column("season_id", sa.String(length=120), nullable=True),
        sa.Column("home_external_team_id", sa.String(length=120), nullable=False),
        sa.Column("away_external_team_id", sa.String(length=120), nullable=False),
        sa.Column("home_name", sa.String(length=160), nullable=False),
        sa.Column("away_name", sa.String(length=160), nullable=False),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SCHEDULED"),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("result_info", sa.String(length=240), nullable=True),
        sa.Column("last_provider_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["competition_id"], ["competitions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_fixture_id", name="uq_fixtures_provider_external"),
    )
    op.create_table(
        "team_fixture_links",
        sa.Column("fixture_id", sa.Uuid(), nullable=False),
        sa.Column("team_profile_id", sa.Uuid(), nullable=False),
        sa.Column("team_side", sa.String(length=8), nullable=False),
        sa.CheckConstraint("team_side IN ('home', 'away')", name="ck_team_fixture_links_side"),
        sa.ForeignKeyConstraint(["fixture_id"], ["fixtures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_profile_id"], ["team_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("fixture_id", "team_profile_id"),
    )


def downgrade() -> None:
    op.drop_table("team_fixture_links")
    op.drop_table("fixtures")
    op.drop_table("team_competitions")
    op.drop_table("team_rivalries")
    op.drop_table("competitions")
    op.drop_index("ix_team_profiles_slug", table_name="team_profiles")
    op.drop_table("team_profiles")
