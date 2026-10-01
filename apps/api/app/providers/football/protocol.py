from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.providers.football.models import (
    FootballFixture,
    FootballTeam,
    ProviderCapabilities,
)


class FootballDataProvider(Protocol):
    """Replaceable source of football data used by domain services."""

    name: str
    capabilities: ProviderCapabilities

    async def get_team(self, external_team_id: str) -> FootballTeam: ...

    async def get_fixtures(
        self, external_team_id: str, start: date, end: date
    ) -> list[FootballFixture]: ...

    async def get_fixture(self, external_fixture_id: str) -> FootballFixture: ...

    async def get_fixture_statistics(self, external_fixture_id: str) -> list[dict[str, Any]]: ...

    async def get_lineups(self, external_fixture_id: str) -> list[dict[str, Any]]: ...

    async def get_events(self, external_fixture_id: str) -> list[dict[str, Any]]: ...

    async def get_xg(self, external_fixture_id: str) -> dict[str, Any] | list[Any] | None: ...
