from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

JsonValue = dict[str, Any] | list[Any]
JsonColumn = JSON().with_variant(JSONB, "postgresql")


class TeamProfile(Base):
    __tablename__ = "team_profiles"
    __table_args__ = (
        CheckConstraint("emotion_base_level BETWEEN 0 AND 100", name="ck_team_profiles_emotion"),
        CheckConstraint("provocation_level BETWEEN 0 AND 100", name="ck_team_profiles_provocation"),
        CheckConstraint("humor_level BETWEEN 0 AND 100", name="ck_team_profiles_humor"),
        CheckConstraint(
            "technical_depth BETWEEN 0 AND 100", name="ck_team_profiles_technical_depth"
        ),
        CheckConstraint("rivalry_boost BETWEEN 0 AND 100", name="ck_team_profiles_rivalry_boost"),
        CheckConstraint("optimism_bias BETWEEN 0 AND 100", name="ck_team_profiles_optimism"),
        CheckConstraint(
            "self_criticism_level BETWEEN 0 AND 100", name="ck_team_profiles_self_criticism"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    short_name: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    football_provider: Mapped[str] = mapped_column(String(80), default="sportmonks")
    external_team_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), default="UTC")
    primary_script_language: Mapped[str] = mapped_column(String(16))
    locale: Mapped[str] = mapped_column(String(16))
    cultural_context: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    fan_identity: Mapped[str] = mapped_column(String(240))
    character_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    character_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    speech_rate_wpm: Mapped[int] = mapped_column(Integer, default=150)
    default_duration_mode: Mapped[str] = mapped_column(String(16), default="AUTO")
    forced_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prematch_offset_minutes: Mapped[int] = mapped_column(Integer, default=360)
    postmatch_delay_minutes: Mapped[int] = mapped_column(Integer, default=10)
    validation_mode: Mapped[str] = mapped_column(String(32), default="HUMAN_REQUIRED")
    emotion_base_level: Mapped[int] = mapped_column(Integer, default=50)
    provocation_level: Mapped[int] = mapped_column(Integer, default=50)
    humor_level: Mapped[int] = mapped_column(Integer, default=50)
    technical_depth: Mapped[int] = mapped_column(Integer, default=50)
    rivalry_boost: Mapped[int] = mapped_column(Integer, default=0)
    optimism_bias: Mapped[int] = mapped_column(Integer, default=50)
    self_criticism_level: Mapped[int] = mapped_column(Integer, default=50)
    allowed_slang: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    forbidden_phrases: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    favorite_expressions: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    editorial_rules: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    profile_version: Mapped[int] = mapped_column(Integer, default=1)

    rivalries: Mapped[list[TeamRivalry]] = relationship(
        back_populates="team_profile", cascade="all, delete-orphan"
    )
    competitions: Mapped[list[TeamCompetition]] = relationship(
        back_populates="team_profile", cascade="all, delete-orphan"
    )
    fixture_links: Mapped[list[TeamFixtureLink]] = relationship(
        back_populates="team_profile", cascade="all, delete-orphan"
    )
    generation_jobs: Mapped[list[GenerationJob]] = relationship(
        back_populates="team_profile", cascade="all, delete-orphan"
    )
    insight_candidates: Mapped[list[InsightCandidate]] = relationship(
        back_populates="team_profile", cascade="all, delete-orphan"
    )
    content_packs: Mapped[list[ContentPack]] = relationship(
        back_populates="team_profile", cascade="all, delete-orphan"
    )


class TeamRivalry(Base):
    __tablename__ = "team_rivalries"
    __table_args__ = (
        UniqueConstraint(
            "team_profile_id", "opponent_external_team_id", name="uq_team_rivalries_opponent"
        ),
        CheckConstraint("intensity BETWEEN 0 AND 100", name="ck_team_rivalries_intensity"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    team_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("team_profiles.id", ondelete="CASCADE")
    )
    opponent_external_team_id: Mapped[str] = mapped_column(String(120))
    opponent_name: Mapped[str] = mapped_column(String(160))
    intensity: Mapped[int] = mapped_column(Integer)
    rivalry_label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    custom_character_rules: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)

    team_profile: Mapped[TeamProfile] = relationship(back_populates="rivalries")


class Competition(Base):
    __tablename__ = "competitions"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_competition_id", name="uq_competitions_provider_external"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(80))
    external_competition_id: Mapped[str] = mapped_column(String(120))
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    team_profiles: Mapped[list[TeamCompetition]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )


class TeamCompetition(Base):
    __tablename__ = "team_competitions"

    team_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("team_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    competition_id: Mapped[UUID] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), primary_key=True
    )

    team_profile: Mapped[TeamProfile] = relationship(back_populates="competitions")
    competition: Mapped[Competition] = relationship(back_populates="team_profiles")


class Fixture(Base):
    __tablename__ = "fixtures"
    __table_args__ = (
        UniqueConstraint("provider", "external_fixture_id", name="uq_fixtures_provider_external"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(80))
    external_fixture_id: Mapped[str] = mapped_column(String(120))
    competition_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("competitions.id"), nullable=True
    )
    season_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    home_external_team_id: Mapped[str] = mapped_column(String(120))
    away_external_team_id: Mapped[str] = mapped_column(String(120))
    home_name: Mapped[str] = mapped_column(String(160))
    away_name: Mapped[str] = mapped_column(String(160))
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED")
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_info: Mapped[str | None] = mapped_column(String(240), nullable=True)
    last_provider_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JsonColumn, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team_links: Mapped[list[TeamFixtureLink]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )
    generation_jobs: Mapped[list[GenerationJob]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )
    team_match_stats: Mapped[list[TeamMatchStat]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )
    player_match_stats: Mapped[list[PlayerMatchStat]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )
    match_events: Mapped[list[MatchEvent]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )
    insight_candidates: Mapped[list[InsightCandidate]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )
    content_packs: Mapped[list[ContentPack]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )


class TeamFixtureLink(Base):
    __tablename__ = "team_fixture_links"
    __table_args__ = (
        CheckConstraint("team_side IN ('home', 'away')", name="ck_team_fixture_links_side"),
    )

    fixture_id: Mapped[UUID] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), primary_key=True
    )
    team_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("team_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    team_side: Mapped[str] = mapped_column(String(8))

    fixture: Mapped[Fixture] = relationship(back_populates="team_links")
    team_profile: Mapped[TeamProfile] = relationship(back_populates="fixture_links")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_generation_jobs_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    team_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("team_profiles.id", ondelete="CASCADE"), index=True
    )
    fixture_id: Mapped[UUID] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    idempotency_key: Mapped[str] = mapped_column(String(300), unique=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)

    team_profile: Mapped[TeamProfile] = relationship(back_populates="generation_jobs")
    fixture: Mapped[Fixture] = relationship(back_populates="generation_jobs")
    content_packs: Mapped[list[ContentPack]] = relationship(back_populates="generation_job")


class TeamMatchStat(Base):
    """One normalized, provider-backed metric for a team in a fixture."""

    __tablename__ = "team_match_stats"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id", "team_external_id", "metric_code", "period", name="uq_team_match_stat"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    fixture_id: Mapped[UUID] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), index=True
    )
    team_external_id: Mapped[str] = mapped_column(String(120), index=True)
    metric_code: Mapped[str] = mapped_column(String(80), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    metric_unit: Mapped[str] = mapped_column(String(24), default="count")
    period: Mapped[str] = mapped_column(String(24), default="ALL")
    provider_type_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fixture: Mapped[Fixture] = relationship(back_populates="team_match_stats")


class PlayerMatchStat(Base):
    """One normalized player metric. Per-90 calculations are derived, never guessed."""

    __tablename__ = "player_match_stats"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id", "player_external_id", "metric_code", "period", name="uq_player_match_stat"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    fixture_id: Mapped[UUID] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), index=True
    )
    player_external_id: Mapped[str] = mapped_column(String(120), index=True)
    player_name: Mapped[str] = mapped_column(String(180))
    team_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    minutes_played: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_code: Mapped[str] = mapped_column(String(80), index=True)
    metric_value: Mapped[float] = mapped_column(Float)
    metric_unit: Mapped[str] = mapped_column(String(24), default="count")
    period: Mapped[str] = mapped_column(String(24), default="ALL")
    provider_type_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fixture: Mapped[Fixture] = relationship(back_populates="player_match_stats")


class MatchEvent(Base):
    __tablename__ = "match_events"
    __table_args__ = (
        UniqueConstraint("fixture_id", "provider_event_id", name="uq_match_event_provider_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    fixture_id: Mapped[UUID] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), index=True
    )
    provider_event_id: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(80))
    minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    player_external_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    player_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    source: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fixture: Mapped[Fixture] = relationship(back_populates="match_events")


class Baseline(Base):
    """Deterministic historical aggregate stored for auditability and display."""

    __tablename__ = "baselines"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_external_id",
            "competition_id",
            "metric_code",
            "window_type",
            "context_key",
            name="uq_baseline_context",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    entity_external_id: Mapped[str] = mapped_column(String(120), index=True)
    competition_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("competitions.id"), nullable=True
    )
    metric_code: Mapped[str] = mapped_column(String(80), index=True)
    window_type: Mapped[str] = mapped_column(String(48))
    window_size: Mapped[int] = mapped_column(Integer)
    context_key: Mapped[str] = mapped_column(String(240))
    context: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    sample_size: Mapped[int] = mapped_column(Integer)
    mean_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    median_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    stddev_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MetricDefinition(Base):
    """Editable central registry for the metrics the deterministic engine may use."""

    __tablename__ = "metric_definitions"

    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(160))
    scope: Mapped[str] = mapped_column(String(16), index=True)
    unit: Mapped[str] = mapped_column(String(24))
    higher_is_better: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    importance_weight: Mapped[float] = mapped_column(Float, default=0.5)
    editorial_weight: Mapped[float] = mapped_column(Float, default=0.5)
    default_anomaly_threshold: Mapped[float] = mapped_column(Float)
    metric_floor: Mapped[float] = mapped_column(Float, default=1.0)
    min_sample_size: Mapped[int] = mapped_column(Integer, default=3)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    provider_mapping: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class InsightCandidate(Base):
    """A factual, auditable analytical result; never an LLM assertion."""

    __tablename__ = "insight_candidates"
    __table_args__ = (
        UniqueConstraint(
            "fixture_id",
            "team_profile_id",
            "content_type",
            "calculation_key",
            name="uq_insight_candidate_calculation",
        ),
        CheckConstraint("final_score BETWEEN 0 AND 100", name="ck_insight_candidates_final_score"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    fixture_id: Mapped[UUID] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), index=True
    )
    team_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("team_profiles.id", ondelete="CASCADE"), index=True
    )
    content_type: Mapped[str] = mapped_column(String(32), index=True)
    calculation_key: Mapped[str] = mapped_column(String(180))
    insight_type: Mapped[str] = mapped_column(String(80), index=True)
    headline_internal: Mapped[str] = mapped_column(String(240))
    claim: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    baseline: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    metric_codes: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    deviation_score: Mapped[float] = mapped_column(Float, default=0.0)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    context_score: Mapped[float] = mapped_column(Float, default=0.0)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    final_score: Mapped[int] = mapped_column(Integer, default=0)
    direction: Mapped[str] = mapped_column(String(16), default="NEUTRAL")
    eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fixture: Mapped[Fixture] = relationship(back_populates="insight_candidates")
    team_profile: Mapped[TeamProfile] = relationship(back_populates="insight_candidates")


class ContentPack(Base):
    """Persisted, auditable output from the Script Engine; human review remains mandatory."""

    __tablename__ = "content_packs"
    __table_args__ = (
        UniqueConstraint("generation_job_id", name="uq_content_packs_generation_job"),
        UniqueConstraint(
            "fixture_id",
            "team_profile_id",
            "content_type",
            "revision_number",
            name="uq_content_packs_fixture_revision",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    team_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("team_profiles.id", ondelete="CASCADE"), index=True
    )
    fixture_id: Mapped[UUID] = mapped_column(
        ForeignKey("fixtures.id", ondelete="CASCADE"), index=True
    )
    generation_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True, unique=True
    )
    content_type: Mapped[str] = mapped_column(String(32), index=True)
    revision_number: Mapped[int] = mapped_column(Integer, default=1)
    team_profile_version: Mapped[int] = mapped_column(Integer, default=1)
    revised_from_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("content_packs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    revision_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="NEEDS_REVIEW", index=True)
    language: Mapped[str] = mapped_column(String(16))
    target_duration_seconds: Mapped[int] = mapped_column(Integer)
    target_word_count: Mapped[int] = mapped_column(Integer)
    estimated_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    emotion: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    narrative_angle: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    selected_insights: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    hooks: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    recommended_hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(240), nullable=True)
    first_screen_text: Mapped[str | None] = mapped_column(String(240), nullable=True)
    script: Mapped[str | None] = mapped_column(Text, nullable=True)
    segments: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    hashtags: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    editorial_tags: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    evidence_manifest: Mapped[list[Any]] = mapped_column(JsonColumn, default=list)
    quality_checks: Mapped[dict[str, Any]] = mapped_column(JsonColumn, default=dict)
    quality_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_version: Mapped[str] = mapped_column(String(80))
    llm_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    original_generated_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JsonColumn, nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    team_profile: Mapped[TeamProfile] = relationship(back_populates="content_packs")
    fixture: Mapped[Fixture] = relationship(back_populates="content_packs")
    generation_job: Mapped[GenerationJob | None] = relationship(back_populates="content_packs")
    revised_from: Mapped[ContentPack | None] = relationship(remote_side=[id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
    approved_by: Mapped[User | None] = relationship(foreign_keys=[approved_by_id])
    performances: Mapped[list[ContentPerformance]] = relationship(
        back_populates="content_pack", cascade="all, delete-orphan"
    )


class User(Base):
    """Single-admin-ready identity model; role expansion stays intentionally out of V1."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContentPerformance(Base):
    """Manual or future-provider measurement snapshot; it never changes content facts."""

    __tablename__ = "content_performance"
    __table_args__ = (
        UniqueConstraint(
            "content_pack_id", "platform", "measured_at", name="uq_content_performance_measurement"
        ),
        CheckConstraint("views >= 0", name="ck_content_performance_views"),
        CheckConstraint("likes >= 0", name="ck_content_performance_likes"),
        CheckConstraint("comments >= 0", name="ck_content_performance_comments"),
        CheckConstraint("shares >= 0", name="ck_content_performance_shares"),
        CheckConstraint(
            "average_percentage_viewed IS NULL OR average_percentage_viewed BETWEEN 0 AND 100",
            name="ck_content_performance_percentage",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    content_pack_id: Mapped[UUID] = mapped_column(
        ForeignKey("content_packs.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(40), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    engaged_views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_watch_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_percentage_viewed: Mapped[float | None] = mapped_column(Float, nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    followers_gained: Mapped[int | None] = mapped_column(Integer, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    content_pack: Mapped[ContentPack] = relationship(back_populates="performances")
