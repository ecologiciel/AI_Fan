from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class FixtureStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    HALF_TIME = "HALF_TIME"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    ABANDONED = "ABANDONED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ProviderCapabilities:
    fixture_stats: bool
    player_stats: bool
    events: bool
    xg_team: bool
    xg_player: bool
    tracking: bool


@dataclass(frozen=True)
class FootballTeam:
    external_id: str
    name: str
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class FootballFixture:
    provider: str
    external_fixture_id: str
    competition_external_id: str | None
    competition_name: str | None
    competition_country: str | None
    season_id: str | None
    home_external_team_id: str
    away_external_team_id: str
    home_name: str
    away_name: str
    kickoff_at: datetime
    status: FixtureStatus
    home_score: int | None
    away_score: int | None
    result_info: str | None
    raw_payload: dict[str, Any]


class FootballProviderError(Exception):
    """A provider failure that callers can surface without corrupting local data."""


class ProviderConfigurationError(FootballProviderError):
    """The provider lacks required runtime configuration."""


class ProviderDataError(FootballProviderError):
    """The provider returned a payload that cannot safely be normalized."""
