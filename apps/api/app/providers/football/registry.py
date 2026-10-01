from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.providers.football.models import FootballProviderError
from app.providers.football.protocol import FootballDataProvider
from app.providers.football.sportmonks.client import SportmonksProvider


class FootballProviderRegistry:
    """Explicit provider lookup; business services never instantiate adapters directly."""

    def __init__(self, providers: list[FootballDataProvider]) -> None:
        self._providers = {provider.name: provider for provider in providers}

    def get(self, name: str) -> FootballDataProvider:
        try:
            return self._providers[name]
        except KeyError as error:
            raise FootballProviderError(f"Unsupported football provider: {name}") from error


@lru_cache
def get_football_provider_registry() -> FootballProviderRegistry:
    settings = get_settings()
    return FootballProviderRegistry(
        [
            SportmonksProvider(
                api_token=settings.sportmonks_api_token,
                base_url=settings.sportmonks_base_url,
                timeout_seconds=settings.provider_timeout_seconds,
            )
        ]
    )
