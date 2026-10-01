import asyncio
import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Competition, Fixture, TeamFixtureLink, TeamProfile
from app.main import app
from app.providers.football.models import FootballFixture, ProviderCapabilities
from app.providers.football.registry import FootballProviderRegistry, get_football_provider_registry
from app.providers.football.sportmonks.mapper import map_fixture
from app.services.match_sync import MatchSyncService

FIXTURES_ROOT = Path(__file__).parents[3] / "fixtures"


class FakeFootballProvider:
    name = "fake"
    capabilities = ProviderCapabilities(True, True, True, False, False, False)

    def __init__(self, fixtures: list[FootballFixture]) -> None:
        self.fixtures = fixtures

    async def get_team(self, external_team_id: str) -> object:
        raise AssertionError("not used by sync")

    async def get_fixtures(
        self, external_team_id: str, start: date, end: date
    ) -> list[FootballFixture]:
        assert external_team_id == "100"
        return self.fixtures

    async def get_fixture(self, external_fixture_id: str) -> FootballFixture:
        return self.fixtures[0]

    async def get_fixture_statistics(self, external_fixture_id: str) -> list[dict[str, object]]:
        return []

    async def get_lineups(self, external_fixture_id: str) -> list[dict[str, object]]:
        return []

    async def get_events(self, external_fixture_id: str) -> list[dict[str, object]]:
        return []

    async def get_xg(self, external_fixture_id: str) -> None:
        return None


def _source_fixture(name: str) -> FootballFixture:
    raw = json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))
    return map_fixture(raw)


def test_sync_upserts_fixture_links_competition_and_raw_payload(session: Session) -> None:
    profile = TeamProfile(
        slug="barcelona-sync",
        display_name="FC Barcelona",
        short_name="Barça",
        football_provider="fake",
        external_team_id="100",
        primary_script_language="es",
        locale="es-ES",
        fan_identity="native_catalan_barca_supporter",
    )
    session.add(profile)
    session.commit()
    service = MatchSyncService()

    first_provider = FakeFootballProvider([_source_fixture("barcelona_future_match.json")])
    first_result = asyncio.run(
        service.sync_team(
            session,
            FootballProviderRegistry([first_provider]),
            profile.id,
            date(2030, 5, 1),
            date(2030, 6, 1),
        )
    )

    assert first_result.created == 1
    fixture = session.scalar(select(Fixture))
    assert fixture is not None
    assert fixture.status == "SCHEDULED"
    assert fixture.raw_payload["id"] == 9001
    assert session.scalar(select(Competition)).name == "Synthetic League"
    assert session.scalar(select(TeamFixtureLink)).team_side == "home"

    second_provider = FakeFootballProvider([_source_fixture("barcelona_finished_match.json")])
    second_result = asyncio.run(
        service.sync_team(
            session,
            FootballProviderRegistry([second_provider]),
            profile.id,
            date(2030, 5, 1),
            date(2030, 6, 1),
        )
    )
    session.refresh(fixture)

    assert second_result.updated == 1
    assert fixture.status == "FINISHED"
    assert (fixture.home_score, fixture.away_score) == (2, 1)


def test_sync_and_fixture_endpoints_use_the_provider_registry(
    authenticated_client: TestClient, session: Session
) -> None:
    profile = TeamProfile(
        slug="endpoint-team",
        display_name="Endpoint Team",
        short_name="Endpoint",
        football_provider="fake",
        external_team_id="100",
        primary_script_language="en",
        locale="en-GB",
        fan_identity="test_supporter",
    )
    session.add(profile)
    session.commit()
    registry = FootballProviderRegistry(
        [FakeFootballProvider([_source_fixture("barcelona_future_match.json")])]
    )
    app.dependency_overrides[get_football_provider_registry] = lambda: registry
    try:
        sync_response = authenticated_client.post(f"/api/v1/teams/{profile.id}/sync")
        fixtures_response = authenticated_client.get(f"/api/v1/fixtures?team_id={profile.id}")
    finally:
        app.dependency_overrides.pop(get_football_provider_registry, None)

    assert sync_response.status_code == 200
    assert sync_response.json()["created"] == 1
    assert fixtures_response.status_code == 200
    assert fixtures_response.json()[0]["external_fixture_id"] == "9001"
