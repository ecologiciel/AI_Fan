from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import date
from typing import Any

import httpx

from app.providers.football.models import (
    FootballFixture,
    FootballProviderError,
    FootballTeam,
    ProviderCapabilities,
    ProviderConfigurationError,
)
from app.providers.football.protocol import FootballDataProvider
from app.providers.football.sportmonks.mapper import map_fixture, map_team


class SportmonksProvider(FootballDataProvider):
    """HTTP adapter for Sportmonks Football API v3 only."""

    name = "sportmonks"
    capabilities = ProviderCapabilities(
        fixture_stats=True,
        player_stats=True,
        events=True,
        xg_team=True,
        xg_player=True,
        tracking=False,
    )

    def __init__(
        self,
        api_token: str | None,
        base_url: str,
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_token = api_token
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._client = client

    async def get_team(self, external_team_id: str) -> FootballTeam:
        data = await self._get_item(f"teams/{external_team_id}")
        return map_team(data)

    async def get_fixtures(
        self, external_team_id: str, start: date, end: date
    ) -> list[FootballFixture]:
        payloads = await self._get_collection(
            f"fixtures/between/date/{start.isoformat()}/{end.isoformat()}/{external_team_id}",
            include="participants;scores;state;league;season",
        )
        return [map_fixture(payload) for payload in payloads]

    async def get_fixture(self, external_fixture_id: str) -> FootballFixture:
        data = await self._get_item(
            f"fixtures/{external_fixture_id}",
            include="participants;scores;state;league;season",
        )
        return map_fixture(data)

    async def get_fixture_statistics(self, external_fixture_id: str) -> list[dict[str, Any]]:
        data = await self._get_item(f"fixtures/{external_fixture_id}", include="statistics.type")
        return _list_field(data, "statistics")

    async def get_lineups(self, external_fixture_id: str) -> list[dict[str, Any]]:
        data = await self._get_item(
            f"fixtures/{external_fixture_id}", include="lineups.player;lineups.details.type"
        )
        return _list_field(data, "lineups")

    async def get_events(self, external_fixture_id: str) -> list[dict[str, Any]]:
        data = await self._get_item(f"fixtures/{external_fixture_id}", include="events")
        return _list_field(data, "events")

    async def get_xg(self, external_fixture_id: str) -> dict[str, Any] | list[Any] | None:
        data = await self._get_item(f"fixtures/{external_fixture_id}", include="xGFixture")
        xg = data.get("xGFixture")
        return xg if isinstance(xg, dict | list) else None

    async def _get_item(self, path: str, include: str | None = None) -> dict[str, Any]:
        params = {"include": include} if include else {}
        payload = await self._request(path, params)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise FootballProviderError("Sportmonks returned no object in data")
        return data

    async def _get_collection(self, path: str, include: str | None = None) -> list[dict[str, Any]]:
        page = 1
        records: list[dict[str, Any]] = []
        while True:
            params: dict[str, str | int] = {"page": page}
            if include:
                params["include"] = include
            payload = await self._request(path, params)
            data = payload.get("data")
            if not isinstance(data, list):
                raise FootballProviderError("Sportmonks returned no collection in data")
            records.extend(item for item in data if isinstance(item, dict))
            pagination = payload.get("pagination")
            has_more = pagination.get("has_more") if isinstance(pagination, dict) else False
            if not has_more:
                return records
            page += 1

    async def _request(self, path: str, params: Mapping[str, str | int]) -> dict[str, Any]:
        if not self._api_token:
            raise ProviderConfigurationError("SPORTMONKS_API_TOKEN is not configured")
        query = {"api_token": self._api_token, **params}
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout_seconds)
        try:
            for attempt in range(self._max_retries):
                try:
                    response = await client.get(f"{self._base_url}/{path}", params=query)
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt + 1 < self._max_retries:
                            await asyncio.sleep(0.25 * (2**attempt))
                            continue
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload, dict):
                        raise FootballProviderError("Sportmonks returned invalid JSON")
                    return payload
                except httpx.RequestError as error:
                    if attempt + 1 == self._max_retries:
                        raise FootballProviderError("Sportmonks request failed") from error
                    await asyncio.sleep(0.25 * (2**attempt))
                except httpx.HTTPStatusError as error:
                    raise FootballProviderError(
                        f"Sportmonks returned HTTP {error.response.status_code}"
                    ) from error
            raise FootballProviderError("Sportmonks retry loop ended unexpectedly")
        finally:
            if owns_client:
                await client.aclose()


def _list_field(data: dict[str, Any], name: str) -> list[dict[str, Any]]:
    value = data.get(name)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
