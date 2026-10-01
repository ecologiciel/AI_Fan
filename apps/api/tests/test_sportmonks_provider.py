import asyncio
import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from app.providers.football.models import FixtureStatus, ProviderConfigurationError
from app.providers.football.sportmonks.client import SportmonksProvider
from app.providers.football.sportmonks.mapper import map_fixture, map_status

FIXTURES_ROOT = Path(__file__).parents[3] / "fixtures"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def test_sportmonks_payload_maps_to_normalized_fixture() -> None:
    fixture = map_fixture(_load_fixture("barcelona_finished_match.json"))

    assert fixture.external_fixture_id == "9001"
    assert fixture.status is FixtureStatus.FINISHED
    assert fixture.home_name == "FC Barcelona"
    assert fixture.home_score == 2
    assert fixture.away_score == 1
    assert fixture.kickoff_at.tzinfo is not None


@pytest.mark.parametrize(
    ("source_status", "expected"),
    [
        ("NS", FixtureStatus.SCHEDULED),
        ("HT", FixtureStatus.HALF_TIME),
        ("FT", FixtureStatus.FINISHED),
        ("AET", FixtureStatus.FINISHED),
        ("PEN", FixtureStatus.FINISHED),
        ("POSTP", FixtureStatus.POSTPONED),
        ("CANC", FixtureStatus.CANCELLED),
        ("ABD", FixtureStatus.ABANDONED),
        ("unmapped", FixtureStatus.UNKNOWN),
    ],
)
def test_sportmonks_status_mapping(source_status: str, expected: FixtureStatus) -> None:
    assert map_status({"state": {"short_name": source_status}}) is expected


def test_provider_paginates_and_sends_token_without_real_network() -> None:
    first = _load_fixture("barcelona_future_match.json")
    second = _load_fixture("postponed_match.json")
    requested_pages: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_pages.append(request.url.params["page"])
        assert request.url.params["api_token"] == "test-token"
        if request.url.params["page"] == "1":
            return httpx.Response(200, json={"data": [first], "pagination": {"has_more": True}})
        return httpx.Response(200, json={"data": [second], "pagination": {"has_more": False}})

    async def run() -> list[object]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = SportmonksProvider(
                api_token="test-token", base_url="https://sportmonks.test/v3", client=client
            )
            return await provider.get_fixtures("100", date(2030, 5, 1), date(2030, 5, 31))

    fixtures = asyncio.run(run())
    assert [fixture.external_fixture_id for fixture in fixtures] == ["9001", "9003"]
    assert requested_pages == ["1", "2"]


def test_missing_xg_is_returned_as_absent_data() -> None:
    raw_fixture = _load_fixture("missing_xg_match.json")

    async def run() -> object:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": raw_fixture}))
        ) as client:
            provider = SportmonksProvider("test-token", "https://sportmonks.test", client=client)
            return await provider.get_xg("9002")

    assert asyncio.run(run()) is None


def test_provider_requires_token_before_request() -> None:
    provider = SportmonksProvider(api_token=None, base_url="https://sportmonks.test")

    with pytest.raises(ProviderConfigurationError):
        asyncio.run(provider.get_team("100"))
