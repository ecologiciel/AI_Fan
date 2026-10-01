from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FixtureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    external_fixture_id: str
    competition_id: UUID | None
    season_id: str | None
    home_external_team_id: str
    away_external_team_id: str
    home_name: str
    away_name: str
    kickoff_at: datetime
    status: str
    home_score: int | None
    away_score: int | None
    result_info: str | None
    last_provider_sync_at: datetime | None
    raw_payload: dict[str, Any] | None


class TeamSyncRead(BaseModel):
    team_profile_id: UUID
    created: int
    updated: int
    skipped: int
    warnings: list[str]
    scheduled_jobs_created: int = 0
    scheduled_jobs_rescheduled: int = 0
    scheduled_jobs_cancelled: int = 0


class TeamMatchStatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_external_id: str
    metric_code: str
    metric_value: float
    metric_unit: str
    period: str
    source: str
    confidence: float


class PlayerMatchStatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_external_id: str
    player_name: str
    team_external_id: str | None
    minutes_played: float | None
    metric_code: str
    metric_value: float
    metric_unit: str
    period: str
    source: str
    confidence: float


class FixtureStatisticsRead(BaseModel):
    fixture_id: UUID
    team_stats: list[TeamMatchStatRead]
    player_stats: list[PlayerMatchStatRead]


class StatisticsRefreshRead(BaseModel):
    fixture_id: UUID
    team_stats_upserted: int
    player_stats_upserted: int
    events_upserted: int
    warnings: list[str]


class BaselineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_code: str
    window_type: str
    window_size: int
    sample_size: int
    mean_value: float | None
    median_value: float | None
    stddev_value: float | None
    min_value: float | None
    max_value: float | None
    context: dict[str, Any]


ContentType = Literal["PRE_MATCH", "POST_MATCH"]


class InsightCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_type: ContentType
    insight_type: str
    headline_internal: str
    claim: str
    evidence: list[Any]
    baseline: dict[str, Any]
    metric_codes: list[Any]
    deviation_score: float
    importance_score: float
    confidence_score: float
    context_score: float
    novelty_score: float
    final_score: int
    direction: str
    eligible: bool
    rejection_reason: str | None
    selected: bool = False
