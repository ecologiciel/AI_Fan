from dataclasses import asdict
from datetime import date, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.analytics.engine import AnalyticsEngine
from app.analytics.ranker import InsightRanker
from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.models import TeamProfile, User
from app.providers.football.models import FootballProviderError
from app.providers.football.registry import FootballProviderRegistry, get_football_provider_registry
from app.schemas.editorial import EditorialPackageRead
from app.schemas.fixtures import (
    BaselineRead,
    FixtureRead,
    FixtureStatisticsRead,
    InsightCandidateRead,
    PlayerMatchStatRead,
    StatisticsRefreshRead,
    TeamMatchStatRead,
    TeamSyncRead,
)
from app.services.editorial_context import EditorialContextService
from app.services.match_sync import MatchSyncService
from app.services.scheduler import SchedulerService
from app.services.statistics import BaselineService, StatisticsService

router = APIRouter()
service = MatchSyncService()
scheduler_service = SchedulerService()
statistics_service = StatisticsService()
baseline_service = BaselineService()
analytics_engine = AnalyticsEngine()
insight_ranker = InsightRanker()
editorial_context_service = EditorialContextService()


@router.get("/fixtures", response_model=list[FixtureRead])
def list_fixtures(
    team_id: UUID | None = None,
    status: str | None = None,
    session: Session = Depends(get_db_session),
) -> list[FixtureRead]:
    return [
        FixtureRead.model_validate(fixture)
        for fixture in service.list_fixtures(session, team_id=team_id, status=status)
    ]


@router.get("/fixtures/{fixture_id}", response_model=FixtureRead)
def get_fixture(fixture_id: UUID, session: Session = Depends(get_db_session)) -> FixtureRead:
    try:
        return FixtureRead.model_validate(service.get_fixture(session, fixture_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Fixture not found") from error


@router.post("/fixtures/{fixture_id}/refresh", response_model=FixtureRead)
async def refresh_fixture(
    fixture_id: UUID,
    session: Session = Depends(get_db_session),
    providers: FootballProviderRegistry = Depends(get_football_provider_registry),
    _: User = Depends(get_current_user),
) -> FixtureRead:
    try:
        fixture = await service.refresh_fixture(session, providers, fixture_id)
        return FixtureRead.model_validate(fixture)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Fixture not found") from error
    except FootballProviderError as error:
        raise HTTPException(status_code=502, detail="Football provider refresh failed") from error


@router.post("/fixtures/{fixture_id}/stats/refresh", response_model=StatisticsRefreshRead)
async def refresh_fixture_statistics(
    fixture_id: UUID,
    session: Session = Depends(get_db_session),
    providers: FootballProviderRegistry = Depends(get_football_provider_registry),
    _: User = Depends(get_current_user),
) -> StatisticsRefreshRead:
    try:
        result = await statistics_service.refresh_fixture_stats(session, providers, fixture_id)
        return StatisticsRefreshRead(**result.__dict__)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Fixture not found") from error
    except FootballProviderError as error:
        raise HTTPException(status_code=502, detail="Football provider refresh failed") from error


@router.get("/fixtures/{fixture_id}/stats", response_model=FixtureStatisticsRead)
def get_fixture_statistics(
    fixture_id: UUID,
    team_id: UUID | None = None,
    session: Session = Depends(get_db_session),
) -> FixtureStatisticsRead:
    try:
        fixture = service.get_fixture(session, fixture_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Fixture not found") from error
    team_external_id = None
    if team_id is not None:
        profile = session.get(TeamProfile, team_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Team profile not found")
        team_external_id = profile.external_team_id
    return FixtureStatisticsRead(
        fixture_id=fixture.id,
        team_stats=[
            TeamMatchStatRead.model_validate(item)
            for item in statistics_service.list_team_stats(session, fixture_id, team_external_id)
        ],
        player_stats=[
            PlayerMatchStatRead.model_validate(item)
            for item in statistics_service.list_player_stats(session, fixture_id, team_external_id)
        ],
    )


@router.get("/fixtures/{fixture_id}/baselines", response_model=list[BaselineRead])
def get_fixture_baselines(
    fixture_id: UUID,
    team_id: UUID,
    session: Session = Depends(get_db_session),
) -> list[BaselineRead]:
    try:
        return [
            BaselineRead.model_validate(item)
            for item in baseline_service.calculate_for_fixture(session, fixture_id, team_id)
        ]
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/fixtures/{fixture_id}/insights", response_model=list[InsightCandidateRead])
def list_fixture_insights(
    fixture_id: UUID,
    team_id: UUID,
    content_type: Literal["PRE_MATCH", "POST_MATCH"] = "POST_MATCH",
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[InsightCandidateRead]:
    candidates = analytics_engine.list_candidates(session, fixture_id, team_id, content_type)
    selected_ids = {candidate.id for candidate in insight_ranker.select(candidates)}
    return [
        InsightCandidateRead.model_validate(candidate).model_copy(
            update={"selected": candidate.id in selected_ids}
        )
        for candidate in candidates
    ]


@router.post(
    "/fixtures/{fixture_id}/recalculate-insights", response_model=list[InsightCandidateRead]
)
def recalculate_fixture_insights(
    fixture_id: UUID,
    team_id: UUID,
    content_type: Literal["PRE_MATCH", "POST_MATCH"] = "POST_MATCH",
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[InsightCandidateRead]:
    try:
        candidates = analytics_engine.recalculate(session, fixture_id, team_id, content_type)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    selected_ids = {candidate.id for candidate in insight_ranker.select(candidates)}
    return [
        InsightCandidateRead.model_validate(candidate).model_copy(
            update={"selected": candidate.id in selected_ids}
        )
        for candidate in candidates
    ]


@router.post("/fixtures/{fixture_id}/editorial-context", response_model=EditorialPackageRead)
def build_editorial_context(
    fixture_id: UUID,
    team_id: UUID,
    content_type: Literal["PRE_MATCH", "POST_MATCH"] = "POST_MATCH",
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> EditorialPackageRead:
    try:
        package = editorial_context_service.build(session, fixture_id, team_id, content_type)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return EditorialPackageRead.model_validate(asdict(package))


@router.post("/teams/{team_id}/sync", response_model=TeamSyncRead)
async def sync_team(
    team_id: UUID,
    session: Session = Depends(get_db_session),
    providers: FootballProviderRegistry = Depends(get_football_provider_registry),
    _: User = Depends(get_current_user),
) -> TeamSyncRead:
    today = date.today()
    try:
        result = await service.sync_team(
            session,
            providers,
            team_id,
            start=today - timedelta(days=7),
            end=today + timedelta(days=30),
        )
        schedule_result = scheduler_service.schedule_team_fixtures(session, team_id)
        return TeamSyncRead(
            team_profile_id=result.team_profile_id,
            created=result.created,
            updated=result.updated,
            skipped=result.skipped,
            warnings=result.warnings,
            scheduled_jobs_created=schedule_result.created,
            scheduled_jobs_rescheduled=schedule_result.rescheduled,
            scheduled_jobs_cancelled=schedule_result.cancelled,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Team profile not found") from error
    except FootballProviderError as error:
        raise HTTPException(status_code=502, detail="Football provider sync failed") from error
