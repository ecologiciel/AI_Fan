"""Normalized football statistics and deterministic historical baselines.

Provider payloads are deliberately parsed here, at the application boundary.  The
analytics phase consumes the normalized rows only and never needs Sportmonks-shaped
JSON.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import fmean, median, pstdev
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import (
    Baseline,
    Fixture,
    MatchEvent,
    PlayerMatchStat,
    TeamFixtureLink,
    TeamMatchStat,
    TeamProfile,
)
from app.providers.football.models import FootballProviderError
from app.providers.football.registry import FootballProviderRegistry

TEAM_METRICS: dict[str, tuple[str, str]] = {
    "goals": ("goals", "count"),
    "goals_scored": ("goals", "count"),
    "expected_goals": ("xg", "goals"),
    "xg": ("xg", "goals"),
    "shots": ("shots", "count"),
    "total_shots": ("shots", "count"),
    "shots_on_target": ("shots_on_target", "count"),
    "shots_on_goal": ("shots_on_target", "count"),
    "possession": ("possession_pct", "percent"),
    "ball_possession": ("possession_pct", "percent"),
    "passes": ("passes", "count"),
    "total_passes": ("passes", "count"),
    "pass_accuracy": ("pass_accuracy_pct", "percent"),
    "passes_accurate_percentage": ("pass_accuracy_pct", "percent"),
    "corners": ("corners", "count"),
    "fouls": ("fouls", "count"),
    "yellowcards": ("yellow_cards", "count"),
    "yellow_cards": ("yellow_cards", "count"),
    "redcards": ("red_cards", "count"),
    "red_cards": ("red_cards", "count"),
}
PLAYER_METRICS: dict[str, tuple[str, str]] = {
    **TEAM_METRICS,
    "minutes_played": ("minutes_played", "minutes"),
    "minutes": ("minutes_played", "minutes"),
    "assists": ("assists", "count"),
    "key_passes": ("key_passes", "count"),
    "tackles": ("tackles", "count"),
    "interceptions": ("interceptions", "count"),
}


@dataclass(frozen=True)
class StatisticsRefreshResult:
    fixture_id: UUID
    team_stats_upserted: int
    player_stats_upserted: int
    events_upserted: int
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BaselineCalculation:
    metric_code: str
    window_type: str
    sample_size: int
    mean_value: float | None
    median_value: float | None
    stddev_value: float | None
    min_value: float | None
    max_value: float | None


class StatisticsService:
    async def refresh_fixture_stats(
        self, session: Session, providers: FootballProviderRegistry, fixture_id: UUID
    ) -> StatisticsRefreshResult:
        fixture = session.get(Fixture, fixture_id)
        if fixture is None:
            raise LookupError("Fixture not found")
        provider = providers.get(fixture.provider)
        warnings: list[str] = []

        try:
            stats = await provider.get_fixture_statistics(fixture.external_fixture_id)
        except FootballProviderError as error:
            stats = []
            warnings.append(f"fixture statistics unavailable: {error}")
        try:
            lineups = await provider.get_lineups(fixture.external_fixture_id)
        except FootballProviderError as error:
            lineups = []
            warnings.append(f"lineups unavailable: {error}")
        try:
            events = await provider.get_events(fixture.external_fixture_id)
        except FootballProviderError as error:
            events = []
            warnings.append(f"events unavailable: {error}")
        try:
            xg = await provider.get_xg(fixture.external_fixture_id)
        except FootballProviderError as error:
            xg = None
            warnings.append(f"xG unavailable: {error}")

        team_count = self._upsert_team_stats(session, fixture, stats)
        team_count += self._upsert_xg(session, fixture, xg)
        player_count = self._upsert_player_stats(session, fixture, lineups)
        event_count = self._upsert_events(session, fixture, events)
        session.commit()
        return StatisticsRefreshResult(fixture_id, team_count, player_count, event_count, warnings)

    def list_team_stats(
        self, session: Session, fixture_id: UUID, team_external_id: str | None = None
    ) -> list[TeamMatchStat]:
        statement = select(TeamMatchStat).where(TeamMatchStat.fixture_id == fixture_id)
        if team_external_id:
            statement = statement.where(TeamMatchStat.team_external_id == team_external_id)
        return list(session.scalars(statement.order_by(TeamMatchStat.metric_code)))

    def list_player_stats(
        self, session: Session, fixture_id: UUID, team_external_id: str | None = None
    ) -> list[PlayerMatchStat]:
        statement = select(PlayerMatchStat).where(PlayerMatchStat.fixture_id == fixture_id)
        if team_external_id:
            statement = statement.where(PlayerMatchStat.team_external_id == team_external_id)
        return list(
            session.scalars(
                statement.order_by(PlayerMatchStat.player_name, PlayerMatchStat.metric_code)
            )
        )

    def _upsert_team_stats(
        self, session: Session, fixture: Fixture, rows: Iterable[dict[str, Any]]
    ) -> int:
        count = 0
        for row in rows:
            metric = _metric_from_row(row, TEAM_METRICS)
            team_id = _string_id(row.get("participant_id") or row.get("team_id") or row.get("team"))
            if metric is None or team_id is None:
                continue
            code, unit, value, type_id = metric
            self._upsert_team_stat(
                session, fixture, team_id, code, unit, value, _period(row), type_id
            )
            count += 1
        return count

    def _upsert_xg(
        self, session: Session, fixture: Fixture, payload: dict[str, Any] | list[Any] | None
    ) -> int:
        if payload is None:
            return 0
        rows: list[dict[str, Any]]
        if isinstance(payload, list):
            rows = [row for row in payload if isinstance(row, dict)]
        elif isinstance(payload, dict):
            candidate = payload.get("data") or payload.get("xg") or payload.get("xG")
            rows = candidate if isinstance(candidate, list) else [payload]
        else:
            return 0
        count = 0
        for row in rows:
            team_id = _string_id(row.get("participant_id") or row.get("team_id") or row.get("team"))
            value = _numeric(
                row.get("value") or row.get("xg") or row.get("xG") or row.get("expected_goals")
            )
            if team_id is None or value is None:
                continue
            self._upsert_team_stat(
                session, fixture, team_id, "xg", "goals", value, _period(row), None
            )
            count += 1
        return count

    def _upsert_team_stat(
        self,
        session: Session,
        fixture: Fixture,
        team_id: str,
        code: str,
        unit: str,
        value: float,
        period: str,
        provider_type_id: str | None,
    ) -> None:
        record = session.scalar(
            select(TeamMatchStat).where(
                TeamMatchStat.fixture_id == fixture.id,
                TeamMatchStat.team_external_id == team_id,
                TeamMatchStat.metric_code == code,
                TeamMatchStat.period == period,
            )
        )
        values = {
            "metric_value": value,
            "metric_unit": unit,
            "provider_type_id": provider_type_id,
            "source": fixture.provider,
            "confidence": 1.0,
        }
        if record is None:
            session.add(
                TeamMatchStat(
                    fixture_id=fixture.id,
                    team_external_id=team_id,
                    metric_code=code,
                    period=period,
                    **values,
                )
            )
            return
        for name, item in values.items():
            setattr(record, name, item)

    def _upsert_player_stats(
        self, session: Session, fixture: Fixture, lineups: Iterable[dict[str, Any]]
    ) -> int:
        count = 0
        for lineup in lineups:
            raw_player = lineup.get("player")
            player: dict[str, Any] = raw_player if isinstance(raw_player, dict) else {}
            player_id = _string_id(lineup.get("player_id") or player.get("id"))
            player_name = str(
                player.get("display_name") or player.get("name") or lineup.get("player_name") or ""
            )
            if not player_id or not player_name:
                continue
            team_id = _string_id(lineup.get("team_id") or lineup.get("participant_id"))
            details = lineup.get("details") or lineup.get("statistics") or []
            if not isinstance(details, list):
                continue
            minutes = _minutes_from_details(details)
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                metric = _metric_from_row(detail, PLAYER_METRICS)
                if metric is None:
                    continue
                code, unit, value, type_id = metric
                record = session.scalar(
                    select(PlayerMatchStat).where(
                        PlayerMatchStat.fixture_id == fixture.id,
                        PlayerMatchStat.player_external_id == player_id,
                        PlayerMatchStat.metric_code == code,
                        PlayerMatchStat.period == _period(detail),
                    )
                )
                values = {
                    "player_name": player_name,
                    "team_external_id": team_id,
                    "minutes_played": minutes,
                    "metric_value": value,
                    "metric_unit": unit,
                    "provider_type_id": type_id,
                    "source": fixture.provider,
                    "confidence": 1.0,
                }
                if record is None:
                    session.add(
                        PlayerMatchStat(
                            fixture_id=fixture.id,
                            player_external_id=player_id,
                            metric_code=code,
                            period=_period(detail),
                            **values,
                        )
                    )
                else:
                    for name, item in values.items():
                        setattr(record, name, item)
                count += 1
        return count

    def _upsert_events(
        self, session: Session, fixture: Fixture, events: Iterable[dict[str, Any]]
    ) -> int:
        count = 0
        for event in events:
            provider_id = _string_id(event.get("id"))
            if provider_id is None:
                continue
            record = session.scalar(
                select(MatchEvent).where(
                    MatchEvent.fixture_id == fixture.id,
                    MatchEvent.provider_event_id == provider_id,
                )
            )
            raw_type = event.get("type")
            type_value: dict[str, Any] = raw_type if isinstance(raw_type, dict) else {}
            raw_player = event.get("player")
            player: dict[str, Any] = raw_player if isinstance(raw_player, dict) else {}
            values = {
                "event_type": str(
                    type_value.get("code")
                    or type_value.get("name")
                    or event.get("type")
                    or "unknown"
                ),
                "minute": _integer(event.get("minute") or event.get("minute_number")),
                "extra_minute": _integer(event.get("extra_minute") or event.get("extra")),
                "team_external_id": _string_id(event.get("participant_id") or event.get("team_id")),
                "player_external_id": _string_id(event.get("player_id") or player.get("id")),
                "player_name": str(player.get("display_name") or player.get("name") or "") or None,
                "payload": event,
                "source": fixture.provider,
            }
            if record is None:
                session.add(
                    MatchEvent(fixture_id=fixture.id, provider_event_id=provider_id, **values)
                )
            else:
                for name, item in values.items():
                    setattr(record, name, item)
            count += 1
        return count


class BaselineService:
    WINDOWS = ("LAST_5", "LAST_10", "SEASON", "HOME_LAST_5", "AWAY_LAST_5", "COMPETITION_LAST_5")

    def calculate_for_fixture(
        self, session: Session, fixture_id: UUID, team_profile_id: UUID
    ) -> list[Baseline]:
        fixture = session.get(Fixture, fixture_id)
        profile = session.get(TeamProfile, team_profile_id)
        link = session.get(
            TeamFixtureLink, {"fixture_id": fixture_id, "team_profile_id": team_profile_id}
        )
        if fixture is None or profile is None or link is None or not profile.external_team_id:
            raise LookupError("Fixture is not linked to a configured team profile")
        metrics = self._metric_codes_for_fixture(session, fixture_id, profile.external_team_id)
        baselines: list[Baseline] = []
        for metric_code in metrics:
            history = self._history(session, fixture, profile.external_team_id, metric_code)
            for window_type in self.WINDOWS:
                selected = self._window(history, fixture, profile.external_team_id, window_type)
                baseline = self._upsert_baseline(
                    session, fixture, profile, metric_code, window_type, selected
                )
                baselines.append(baseline)
        session.commit()
        return baselines

    @staticmethod
    def _metric_codes_for_fixture(
        session: Session, fixture_id: UUID, team_external_id: str
    ) -> list[str]:
        statement = select(TeamMatchStat.metric_code).where(
            TeamMatchStat.fixture_id == fixture_id,
            TeamMatchStat.team_external_id == team_external_id,
        )
        return sorted(set(session.scalars(statement)))

    @staticmethod
    def _history(
        session: Session, target: Fixture, team_external_id: str, metric_code: str
    ) -> list[tuple[Fixture, float]]:
        statement = (
            select(Fixture, TeamMatchStat.metric_value)
            .join(TeamMatchStat, TeamMatchStat.fixture_id == Fixture.id)
            .where(
                TeamMatchStat.team_external_id == team_external_id,
                TeamMatchStat.metric_code == metric_code,
                TeamMatchStat.period == "ALL",
                Fixture.status == "FINISHED",
                Fixture.id != target.id,
                Fixture.kickoff_at < target.kickoff_at,
            )
            .order_by(Fixture.kickoff_at.desc())
        )
        return [(row[0], float(row[1])) for row in session.execute(statement)]

    @staticmethod
    def _window(
        history: list[tuple[Fixture, float]],
        target: Fixture,
        team_external_id: str,
        window_type: str,
    ) -> list[float]:
        if window_type == "LAST_5":
            rows = history[:5]
        elif window_type == "LAST_10":
            rows = history[:10]
        elif window_type == "SEASON":
            rows = (
                [row for row in history if row[0].season_id == target.season_id]
                if target.season_id
                else []
            )
        elif window_type == "HOME_LAST_5":
            rows = [row for row in history if row[0].home_external_team_id == team_external_id][:5]
        elif window_type == "AWAY_LAST_5":
            rows = [row for row in history if row[0].away_external_team_id == team_external_id][:5]
        else:
            rows = [row for row in history if row[0].competition_id == target.competition_id][:5]
        return [float(value) for _, value in rows]

    def _upsert_baseline(
        self,
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        metric_code: str,
        window_type: str,
        values: list[float],
    ) -> Baseline:
        context_key = f"fixture:{fixture.id}:team:{profile.id}"
        statement = select(Baseline).where(
            Baseline.entity_type == "team",
            Baseline.entity_external_id == profile.external_team_id,
            Baseline.competition_id == fixture.competition_id,
            Baseline.metric_code == metric_code,
            Baseline.window_type == window_type,
            Baseline.context_key == context_key,
        )
        if fixture.competition_id is None:
            statement = statement.where(Baseline.competition_id.is_(None))
        record = session.scalar(statement)
        aggregate = _aggregate(metric_code, window_type, values)
        values_to_save = {
            "window_size": _window_size(window_type),
            "context": {"fixture_id": str(fixture.id), "team_profile_id": str(profile.id)},
            **aggregate,
            "calculated_at": datetime.now(UTC),
        }
        if record is None:
            record = Baseline(
                entity_type="team",
                entity_external_id=profile.external_team_id or "",
                competition_id=fixture.competition_id,
                metric_code=metric_code,
                window_type=window_type,
                context_key=context_key,
                **values_to_save,
            )
            session.add(record)
        else:
            for name, item in values_to_save.items():
                setattr(record, name, item)
        return record


def _metric_from_row(
    row: dict[str, Any], mapping: dict[str, tuple[str, str]]
) -> tuple[str, str, float, str | None] | None:
    type_value = row.get("type")
    raw_type: dict[str, Any] = type_value if isinstance(type_value, dict) else {}
    raw_code = (
        raw_type.get("code") or raw_type.get("name") or row.get("metric_code") or row.get("type")
    )
    if not isinstance(raw_code, str):
        return None
    normalized_code = raw_code.lower().replace("-", "_").replace(" ", "_")
    mapped = mapping.get(normalized_code)
    value_source = row.get("data") if isinstance(row.get("data"), dict) else row
    value = _numeric(value_source.get("value") if isinstance(value_source, dict) else None)
    if mapped is None or value is None:
        return None
    return mapped[0], mapped[1], value, _string_id(raw_type.get("id"))


def _minutes_from_details(details: list[Any]) -> float | None:
    for detail in details:
        if not isinstance(detail, dict):
            continue
        metric = _metric_from_row(detail, PLAYER_METRICS)
        if metric and metric[0] == "minutes_played":
            return metric[2]
    return None


def _period(row: dict[str, Any]) -> str:
    value = row.get("period") or row.get("period_name") or "ALL"
    return str(value).upper()


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().rstrip("%"))
        except ValueError:
            return None
    return None


def _integer(value: Any) -> int | None:
    number = _numeric(value)
    return int(number) if number is not None else None


def _string_id(value: Any) -> str | None:
    if value is None or isinstance(value, dict | list):
        return None
    return str(value)


def _window_size(window_type: str) -> int:
    return {
        "LAST_5": 5,
        "LAST_10": 10,
        "HOME_LAST_5": 5,
        "AWAY_LAST_5": 5,
        "COMPETITION_LAST_5": 5,
    }.get(window_type, 0)


def _aggregate(metric_code: str, window_type: str, values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "sample_size": 0,
            "mean_value": None,
            "median_value": None,
            "stddev_value": None,
            "min_value": None,
            "max_value": None,
        }
    return {
        "sample_size": len(values),
        "mean_value": fmean(values),
        "median_value": median(values),
        "stddev_value": pstdev(values) if len(values) > 1 else None,
        "min_value": min(values),
        "max_value": max(values),
    }
