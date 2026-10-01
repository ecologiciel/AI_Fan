import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.domain.models import GenerationJob, TeamMatchStat, TeamProfile
from app.providers.football.models import FootballProviderError
from app.providers.football.registry import (
    FootballProviderRegistry,
    get_football_provider_registry,
)
from app.providers.llm.registry import get_llm_provider
from app.services.content_packs import ContentPackService
from app.services.match_sync import MatchSyncService
from app.services.scheduler import PostMatchDataPending, SchedulerService
from app.services.statistics import StatisticsService
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def run() -> None:
    """Periodically synchronize active teams and reserve persisted generation jobs."""
    settings = get_settings()
    settings.validate_runtime_security()
    configure_logging()
    registry = get_football_provider_registry()
    match_sync = MatchSyncService()
    statistics = StatisticsService()
    scheduler = SchedulerService()
    last_sync_at: datetime | None = None
    logger.info("worker started", extra={"app_env": settings.app_env, "status": "ready"})
    while True:
        now = datetime.now(UTC)
        if last_sync_at is None or (now - last_sync_at).total_seconds() >= settings.scheduler_sync_interval_seconds:
            await _sync_active_teams(match_sync, statistics, scheduler, registry)
            last_sync_at = now
        with SessionLocal() as session:
            executor = ContentGenerationJobExecutor(
                session, ContentPackService(get_llm_provider()), statistics, registry
            )
            await scheduler.dispatch_due_jobs(session, executor)
        await asyncio.sleep(settings.scheduler_dispatch_interval_seconds)


async def _sync_active_teams(
    match_sync: MatchSyncService,
    statistics: StatisticsService,
    scheduler: SchedulerService,
    registry: FootballProviderRegistry,
) -> None:
    with SessionLocal() as session:
        team_ids = list(session.scalars(select(TeamProfile.id).where(TeamProfile.active.is_(True))))
        for team_id in team_ids:
            try:
                await match_sync.sync_team(
                    session,
                    registry,
                    team_id,
                    start=datetime.now(UTC).date() - timedelta(days=7),
                    end=datetime.now(UTC).date() + timedelta(days=30),
                )
                for fixture in match_sync.list_fixtures(session, team_id=team_id, status="FINISHED"):
                    result = await statistics.refresh_fixture_stats(session, registry, fixture.id)
                    for warning in result.warnings:
                        logger.info(
                            "statistics feed unavailable",
                            extra={"fixture_id": str(fixture.id), "warning": warning},
                        )
                scheduler.schedule_team_fixtures(session, team_id)
            except FootballProviderError as error:
                logger.warning("team sync failed", extra={"team_profile_id": str(team_id), "error": str(error)})
            except Exception as error:  # noqa: BLE001 - one team must not stop the worker loop
                logger.error(
                    "team sync failed unexpectedly",
                    extra={"team_profile_id": str(team_id), "error_type": type(error).__name__},
                )


class ContentGenerationJobExecutor:
    def __init__(
        self,
        session: Session,
        content_packs: ContentPackService,
        statistics: StatisticsService,
        providers: FootballProviderRegistry,
    ) -> None:
        self._session = session
        self._content_packs = content_packs
        self._statistics = statistics
        self._providers = providers

    async def execute(self, job: GenerationJob) -> None:
        if job.content_type == "POST_MATCH":
            await self._statistics.refresh_fixture_stats(self._session, self._providers, job.fixture_id)
            has_team_statistics = self._session.scalar(
                select(TeamMatchStat.id).where(TeamMatchStat.fixture_id == job.fixture_id).limit(1)
            )
            if has_team_statistics is None and int(
                job.payload.get("postmatch_data_retry_count", 0)
            ) == 0:
                raise PostMatchDataPending("Post-match team statistics are not available yet")
        await self._content_packs.generate(
            self._session, job.fixture_id, job.team_profile_id, job.content_type, generation_job=job
        )


if __name__ == "__main__":
    asyncio.run(run())
