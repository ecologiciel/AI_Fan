from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.providers.football.models import (
    FixtureStatus,
    FootballFixture,
    FootballTeam,
    ProviderDataError,
)

_STATUS_MAP = {
    "NS": FixtureStatus.SCHEDULED,
    "SCHEDULED": FixtureStatus.SCHEDULED,
    "NOT STARTED": FixtureStatus.SCHEDULED,
    "TBA": FixtureStatus.SCHEDULED,
    "1ST": FixtureStatus.LIVE,
    "2ND": FixtureStatus.LIVE,
    "ET": FixtureStatus.LIVE,
    "BT": FixtureStatus.LIVE,
    "LIVE": FixtureStatus.LIVE,
    "INPLAY": FixtureStatus.LIVE,
    "HT": FixtureStatus.HALF_TIME,
    "HALF TIME": FixtureStatus.HALF_TIME,
    "FT": FixtureStatus.FINISHED,
    "AET": FixtureStatus.FINISHED,
    "PEN": FixtureStatus.FINISHED,
    "FINISHED": FixtureStatus.FINISHED,
    "POSTP": FixtureStatus.POSTPONED,
    "POSTPONED": FixtureStatus.POSTPONED,
    "CANC": FixtureStatus.CANCELLED,
    "CANCELLED": FixtureStatus.CANCELLED,
    "ABD": FixtureStatus.ABANDONED,
    "ABANDONED": FixtureStatus.ABANDONED,
}


def map_status(payload: dict[str, Any]) -> FixtureStatus:
    state = payload.get("state")
    state_values = state if isinstance(state, dict) else {}
    candidates = (
        state_values.get("short_name"),
        state_values.get("name"),
        payload.get("status"),
        payload.get("status_name"),
    )
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        normalized = candidate.upper().replace("_", " ").strip()
        if normalized in _STATUS_MAP:
            return _STATUS_MAP[normalized]
    return FixtureStatus.UNKNOWN


def map_team(payload: dict[str, Any]) -> FootballTeam:
    identifier = payload.get("id")
    name = payload.get("name")
    if identifier is None or not isinstance(name, str) or not name:
        raise ProviderDataError("Sportmonks team payload is missing an id or name")
    return FootballTeam(external_id=str(identifier), name=name, raw_payload=payload)


def map_fixture(payload: dict[str, Any]) -> FootballFixture:
    identifier = payload.get("id")
    if identifier is None:
        raise ProviderDataError("Sportmonks fixture payload is missing id")
    home, away = _participants(payload)
    kickoff_at = _parse_datetime(payload.get("starting_at") or payload.get("starting_at_timestamp"))
    home_score, away_score = _scores(payload, home["id"], away["id"])
    league: dict[str, Any] = (
        dict(payload["league"]) if isinstance(payload.get("league"), dict) else {}
    )
    season: dict[str, Any] = (
        dict(payload["season"]) if isinstance(payload.get("season"), dict) else {}
    )
    competition_id = league.get("id") or payload.get("league_id")
    season_id = season.get("id") or payload.get("season_id")
    return FootballFixture(
        provider="sportmonks",
        external_fixture_id=str(identifier),
        competition_external_id=str(competition_id) if competition_id is not None else None,
        competition_name=league.get("name") if isinstance(league.get("name"), str) else None,
        competition_country=league.get("country_name")
        if isinstance(league.get("country_name"), str)
        else None,
        season_id=str(season_id) if season_id is not None else None,
        home_external_team_id=str(home["id"]),
        away_external_team_id=str(away["id"]),
        home_name=str(home["name"]),
        away_name=str(away["name"]),
        kickoff_at=kickoff_at,
        status=map_status(payload),
        home_score=home_score,
        away_score=away_score,
        result_info=payload.get("result_info")
        if isinstance(payload.get("result_info"), str)
        else None,
        raw_payload=payload,
    )


def _participants(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    participants = payload.get("participants")
    if not isinstance(participants, list):
        raise ProviderDataError("Sportmonks fixture payload is missing participants")
    home = _participant_by_location(participants, "home")
    away = _participant_by_location(participants, "away")
    if home is None or away is None:
        raise ProviderDataError("Sportmonks fixture participants lack home or away metadata")
    if (
        home.get("id") is None
        or away.get("id") is None
        or not home.get("name")
        or not away.get("name")
    ):
        raise ProviderDataError("Sportmonks fixture participant is incomplete")
    return home, away


def _participant_by_location(participants: list[object], location: str) -> dict[str, Any] | None:
    for participant in participants:
        if not isinstance(participant, dict):
            continue
        meta = participant.get("meta")
        participant_location = meta.get("location") if isinstance(meta, dict) else None
        if isinstance(participant_location, str) and participant_location.lower() == location:
            return participant
    return None


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    if not isinstance(value, str):
        raise ProviderDataError("Sportmonks fixture payload is missing starting_at")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ProviderDataError("Sportmonks starting_at is not a valid ISO datetime") from error
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _scores(
    payload: dict[str, Any], home_id: object, away_id: object
) -> tuple[int | None, int | None]:
    scores = payload.get("scores")
    if not isinstance(scores, list):
        return None, None
    values: dict[str, tuple[int, int]] = {}
    priority = {"CURRENT": 3, "FT": 4, "2ND_HALF": 2, "1ST_HALF": 1}
    for score in scores:
        if not isinstance(score, dict) or score.get("participant_id") is None:
            continue
        score_value = score.get("score")
        goals = score_value.get("goals") if isinstance(score_value, dict) else score_value
        if not isinstance(goals, int):
            continue
        description = score.get("description")
        score_priority = priority.get(description.upper(), 0) if isinstance(description, str) else 0
        participant_id = str(score["participant_id"])
        if participant_id not in values or score_priority >= values[participant_id][0]:
            values[participant_id] = (score_priority, goals)
    return values.get(str(home_id), (0, None))[1], values.get(str(away_id), (0, None))[1]
