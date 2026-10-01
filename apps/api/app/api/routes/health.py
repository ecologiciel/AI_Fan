from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.providers.football.registry import get_football_provider_registry

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str


class ProviderHealth(BaseModel):
    provider: str
    configured: bool
    capabilities: dict[str, bool] | None = None


class ProvidersHealthResponse(BaseModel):
    status: str
    football: ProviderHealth
    llm: ProviderHealth


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe; it intentionally has no external dependency."""
    return HealthResponse(status="ok", service="api")


@router.get("/health/providers", response_model=ProvidersHealthResponse)
def provider_health() -> ProvidersHealthResponse:
    """Report configuration readiness only; this endpoint never calls external providers."""

    settings = get_settings()
    capabilities: dict[str, bool] | None = None
    try:
        provider = get_football_provider_registry().get(settings.football_provider)
        capabilities = {
            "fixture_stats": provider.capabilities.fixture_stats,
            "player_stats": provider.capabilities.player_stats,
            "events": provider.capabilities.events,
            "xg_team": provider.capabilities.xg_team,
            "xg_player": provider.capabilities.xg_player,
            "tracking": provider.capabilities.tracking,
        }
    except Exception:  # noqa: BLE001 - readiness must stay available for invalid provider settings
        pass
    return ProvidersHealthResponse(
        status="ok",
        football=ProviderHealth(
            provider=settings.football_provider,
            configured=bool(settings.sportmonks_api_token),
            capabilities=capabilities,
        ),
        llm=ProviderHealth(
            provider=settings.llm_provider,
            configured=bool(settings.openai_api_key and settings.llm_model),
        ),
    )
