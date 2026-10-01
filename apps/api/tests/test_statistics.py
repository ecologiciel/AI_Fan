import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Fixture, PlayerMatchStat, TeamFixtureLink, TeamMatchStat, TeamProfile
from app.providers.football.models import ProviderCapabilities
from app.providers.football.registry import FootballProviderRegistry
from app.services.statistics import BaselineService, StatisticsService


class StatisticsProvider:
    name = "fake"
    capabilities = ProviderCapabilities(True, True, True, True, False, False)

    async def get_team(self, external_team_id: str) -> object:
        raise AssertionError("not used")

    async def get_fixtures(self, *args: object) -> list[object]:
        raise AssertionError("not used")

    async def get_fixture(self, external_fixture_id: str) -> object:
        raise AssertionError("not used")

    async def get_fixture_statistics(self, external_fixture_id: str) -> list[dict[str, object]]:
        return [
            {"participant_id": "barca", "type": {"id": 1, "code": "shots"}, "data": {"value": 12}},
            {
                "participant_id": "barca",
                "type": {"id": 2, "code": "possession"},
                "data": {"value": "62%"},
            },
            {"participant_id": "rival", "type": {"id": 1, "code": "shots"}, "data": {"value": 8}},
        ]

    async def get_lineups(self, external_fixture_id: str) -> list[dict[str, object]]:
        return [
            {
                "player_id": "pedri",
                "team_id": "barca",
                "player": {"name": "Pedri"},
                "details": [
                    {"type": {"code": "minutes_played"}, "data": {"value": 75}},
                    {"type": {"code": "key_passes"}, "data": {"value": 4}},
                ],
            }
        ]

    async def get_events(self, external_fixture_id: str) -> list[dict[str, object]]:
        return [{"id": "event-1", "type": {"code": "goal"}, "minute": 15, "team_id": "barca"}]

    async def get_xg(self, external_fixture_id: str) -> list[dict[str, object]]:
        return [{"team_id": "barca", "xg": 1.8}]


def _profile(session: Session) -> TeamProfile:
    profile = TeamProfile(
        slug="stats-team",
        display_name="Stats Team",
        short_name="Stats",
        football_provider="fake",
        external_team_id="barca",
        primary_script_language="es",
        locale="es-ES",
        fan_identity="native_catalan_supporter",
    )
    session.add(profile)
    session.commit()
    return profile


def _fixture(
    session: Session, external_id: str, kickoff_at: datetime, status: str = "FINISHED"
) -> Fixture:
    fixture = Fixture(
        provider="fake",
        external_fixture_id=external_id,
        home_external_team_id="barca",
        away_external_team_id="rival",
        home_name="Barça",
        away_name="Rival",
        kickoff_at=kickoff_at,
        status=status,
        season_id="season-1",
    )
    session.add(fixture)
    session.flush()
    return fixture


def test_normalizes_available_stats_without_requiring_xg_or_complete_payload(
    session: Session,
) -> None:
    fixture = _fixture(session, "fixture-1", datetime.now(UTC))
    session.commit()

    result = asyncio.run(
        StatisticsService().refresh_fixture_stats(
            session, FootballProviderRegistry([StatisticsProvider()]), fixture.id
        )
    )

    assert result.team_stats_upserted == 4
    assert result.player_stats_upserted == 2
    assert result.events_upserted == 1
    assert (
        session.scalar(
            select(TeamMatchStat).where(
                TeamMatchStat.fixture_id == fixture.id,
                TeamMatchStat.team_external_id == "barca",
                TeamMatchStat.metric_code == "xg",
            )
        ).metric_value
        == 1.8
    )
    player_stat = session.scalar(
        select(PlayerMatchStat).where(PlayerMatchStat.metric_code == "key_passes")
    )
    assert player_stat is not None
    assert player_stat.minutes_played == 75


def test_baselines_use_only_prior_finished_matches_and_correct_home_window(
    session: Session,
) -> None:
    profile = _profile(session)
    now = datetime.now(UTC)
    older = _fixture(session, "old-1", now - timedelta(days=3))
    newer = _fixture(session, "old-2", now - timedelta(days=1))
    target = _fixture(session, "target", now + timedelta(days=1), status="SCHEDULED")
    session.add_all(
        [
            TeamFixtureLink(fixture_id=target.id, team_profile_id=profile.id, team_side="home"),
            TeamMatchStat(
                fixture_id=older.id,
                team_external_id="barca",
                metric_code="shots",
                metric_value=8,
                metric_unit="count",
                source="fake",
            ),
            TeamMatchStat(
                fixture_id=newer.id,
                team_external_id="barca",
                metric_code="shots",
                metric_value=12,
                metric_unit="count",
                source="fake",
            ),
            TeamMatchStat(
                fixture_id=target.id,
                team_external_id="barca",
                metric_code="shots",
                metric_value=20,
                metric_unit="count",
                source="fake",
            ),
        ]
    )
    session.commit()

    baselines = BaselineService().calculate_for_fixture(session, target.id, profile.id)

    last_five = next(item for item in baselines if item.window_type == "LAST_5")
    home_last_five = next(item for item in baselines if item.window_type == "HOME_LAST_5")
    assert last_five.sample_size == 2
    assert last_five.mean_value == 10
    assert home_last_five.sample_size == 2
    assert home_last_five.mean_value == 10


def test_statistics_and_baselines_are_available_from_fixture_endpoints(
    client: TestClient, session: Session
) -> None:
    profile = _profile(session)
    now = datetime.now(UTC)
    historical = _fixture(session, "historical", now - timedelta(days=1))
    target = _fixture(session, "endpoint-target", now + timedelta(days=1), status="SCHEDULED")
    session.add_all(
        [
            TeamFixtureLink(fixture_id=target.id, team_profile_id=profile.id, team_side="home"),
            TeamMatchStat(
                fixture_id=historical.id,
                team_external_id="barca",
                metric_code="shots",
                metric_value=9,
                metric_unit="count",
                source="fake",
            ),
            TeamMatchStat(
                fixture_id=target.id,
                team_external_id="barca",
                metric_code="shots",
                metric_value=11,
                metric_unit="count",
                source="fake",
            ),
        ]
    )
    session.commit()

    stats_response = client.get(f"/api/v1/fixtures/{target.id}/stats?team_id={profile.id}")
    baselines_response = client.get(f"/api/v1/fixtures/{target.id}/baselines?team_id={profile.id}")

    assert stats_response.status_code == 200
    assert stats_response.json()["team_stats"][0]["metric_value"] == 11
    assert baselines_response.status_code == 200
    last_five = next(item for item in baselines_response.json() if item["window_type"] == "LAST_5")
    assert last_five["mean_value"] == 9
