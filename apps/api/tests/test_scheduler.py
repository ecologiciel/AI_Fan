import asyncio
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Fixture, GenerationJob, TeamFixtureLink, TeamProfile
from app.services.scheduler import (
    CANCELLED,
    FAILED,
    PENDING,
    POST_MATCH,
    POSTMATCH_DATA_RETRY_SECONDS,
    PRE_MATCH,
    SUCCEEDED,
    PostMatchDataPending,
    SchedulerService,
    build_idempotency_key,
)


class SuccessfulExecutor:
    def __init__(self) -> None:
        self.executed_ids: list[object] = []

    async def execute(self, job: GenerationJob) -> None:
        self.executed_ids.append(job.id)


class FailingExecutor:
    async def execute(self, job: GenerationJob) -> None:
        raise RuntimeError("provider temporarily unavailable")


class MissingPostMatchDataExecutor:
    async def execute(self, job: GenerationJob) -> None:
        raise PostMatchDataPending("Post-match team statistics are not available yet")


def _team_and_fixture(session: Session, kickoff_at: datetime) -> tuple[TeamProfile, Fixture]:
    profile = TeamProfile(
        slug="scheduler-team",
        display_name="Scheduler Team",
        short_name="Scheduler",
        external_team_id="100",
        primary_script_language="en",
        locale="en-GB",
        fan_identity="test_supporter",
        prematch_offset_minutes=360,
        postmatch_delay_minutes=10,
    )
    fixture = Fixture(
        provider="fake",
        external_fixture_id="fixture-1",
        home_external_team_id="100",
        away_external_team_id="200",
        home_name="Home",
        away_name="Away",
        kickoff_at=kickoff_at,
        status="SCHEDULED",
    )
    session.add_all([profile, fixture])
    session.flush()
    session.add(
        TeamFixtureLink(fixture_id=fixture.id, team_profile_id=profile.id, team_side="home")
    )
    session.commit()
    return profile, fixture


def test_prematch_jobs_are_rescheduled_and_idempotent(session: Session) -> None:
    now = datetime(2030, 5, 1, 12, tzinfo=UTC)
    profile, fixture = _team_and_fixture(session, now + timedelta(days=2))
    service = SchedulerService()

    first = service.schedule_team_fixtures(session, profile.id, now)
    second = service.schedule_team_fixtures(session, profile.id, now)
    job = session.scalar(select(GenerationJob))

    assert first.created == 1
    assert second.created == 0
    assert job is not None
    assert job.content_type == PRE_MATCH
    assert job.scheduled_for.replace(tzinfo=UTC) == fixture.kickoff_at - timedelta(hours=6)
    assert job.idempotency_key == build_idempotency_key(profile.id, fixture.id, PRE_MATCH, 1)

    fixture.kickoff_at += timedelta(hours=3)
    updated = service.schedule_team_fixtures(session, profile.id, now)
    session.refresh(job)
    assert updated.rescheduled == 1
    assert job.scheduled_for.replace(tzinfo=UTC) == fixture.kickoff_at - timedelta(hours=6)


def test_finished_fixture_creates_postmatch_once_and_cancels_obsolete_prematch(
    session: Session,
) -> None:
    now = datetime(2030, 5, 3, 12, tzinfo=UTC)
    profile, fixture = _team_and_fixture(session, now + timedelta(days=1))
    service = SchedulerService()
    service.schedule_team_fixtures(session, profile.id, now)

    fixture.status = "FINISHED"
    fixture.last_provider_sync_at = now
    postmatch = service.schedule_team_fixtures(session, profile.id, now)
    jobs = list(session.scalars(select(GenerationJob).order_by(GenerationJob.content_type)))

    assert postmatch.created == 1
    assert {job.content_type for job in jobs} == {PRE_MATCH, POST_MATCH}
    assert next(job for job in jobs if job.content_type == PRE_MATCH).status == CANCELLED
    post_job = next(job for job in jobs if job.content_type == POST_MATCH)
    assert post_job.scheduled_for.replace(tzinfo=UTC) == now + timedelta(minutes=10)

    fixture.last_provider_sync_at = now + timedelta(minutes=3)
    second = service.schedule_team_fixtures(session, profile.id, now)
    assert second.created == 0
    scheduled_for = session.scalar(
        select(GenerationJob.scheduled_for).where(GenerationJob.content_type == POST_MATCH)
    )
    assert scheduled_for is not None
    assert scheduled_for.replace(tzinfo=UTC) == now + timedelta(minutes=10)


def test_profile_version_replaces_pending_automatic_job(session: Session) -> None:
    now = datetime(2030, 5, 1, 12, tzinfo=UTC)
    profile, fixture = _team_and_fixture(session, now + timedelta(days=1))
    service = SchedulerService()
    service.schedule_team_fixtures(session, profile.id, now)

    profile.profile_version = 2
    result = service.schedule_team_fixtures(session, profile.id, now)
    jobs = list(session.scalars(select(GenerationJob).order_by(GenerationJob.idempotency_key)))

    assert result.created == 1
    assert result.cancelled == 1
    assert [job.status for job in jobs] == [CANCELLED, "PENDING"]
    assert jobs[1].idempotency_key.endswith(":v2")


def test_due_job_is_claimed_and_executed_only_once(session: Session) -> None:
    now = datetime(2030, 5, 1, 12, tzinfo=UTC)
    profile, _ = _team_and_fixture(session, now + timedelta(days=1))
    service = SchedulerService()
    service.schedule_team_fixtures(session, profile.id, now)
    executor = SuccessfulExecutor()

    first = asyncio.run(service.dispatch_due_jobs(session, executor, now + timedelta(days=1)))
    second = asyncio.run(service.dispatch_due_jobs(session, executor, now + timedelta(days=1)))
    job = session.scalar(select(GenerationJob))

    assert len(first) == 1
    assert second == []
    assert len(executor.executed_ids) == 1
    assert job is not None and job.status == SUCCEEDED and job.attempt_count == 1


def test_retry_moves_failed_job_back_to_pending(session: Session) -> None:
    now = datetime(2030, 5, 1, 12, tzinfo=UTC)
    profile, _ = _team_and_fixture(session, now + timedelta(days=1))
    service = SchedulerService()
    service.schedule_team_fixtures(session, profile.id, now)
    job = session.scalar(select(GenerationJob))
    assert job is not None
    job.status = FAILED
    session.commit()

    retried = service.retry_job(session, job.id, now)
    assert retried.status == "PENDING"
    assert retried.scheduled_for == now
    assert retried.attempt_count == 0


def test_execution_failures_are_retried_without_creating_duplicate_jobs(session: Session) -> None:
    now = datetime(2030, 5, 1, 12, tzinfo=UTC)
    profile, _ = _team_and_fixture(session, now + timedelta(days=1))
    service = SchedulerService()
    service.schedule_team_fixtures(session, profile.id, now)
    job = session.scalar(select(GenerationJob))
    assert job is not None

    claimed = asyncio.run(
        service.dispatch_due_jobs(session, FailingExecutor(), now + timedelta(days=1))
    )
    session.refresh(job)

    assert len(claimed) == 1
    assert job.status == "PENDING"
    assert job.attempt_count == 1
    assert job.last_error == "provider temporarily unavailable"
    assert len(list(session.scalars(select(GenerationJob)))) == 1


def test_missing_postmatch_statistics_are_replanned_once_after_ten_minutes(
    session: Session,
) -> None:
    now = datetime(2030, 5, 1, 12, tzinfo=UTC)
    profile, fixture = _team_and_fixture(session, now + timedelta(days=1))
    fixture.status = "FINISHED"
    fixture.last_provider_sync_at = now
    session.commit()
    service = SchedulerService()
    service.schedule_team_fixtures(session, profile.id, now)
    job = session.scalar(select(GenerationJob).where(GenerationJob.content_type == POST_MATCH))
    assert job is not None

    asyncio.run(
        service.dispatch_due_jobs(
            session, MissingPostMatchDataExecutor(), now + timedelta(minutes=10)
        )
    )
    session.refresh(job)

    assert job.status == PENDING
    assert job.scheduled_for.replace(tzinfo=UTC) == now + timedelta(
        minutes=10, seconds=POSTMATCH_DATA_RETRY_SECONDS
    )
    assert job.payload["postmatch_data_retry_count"] == 1


def test_jobs_api_lists_and_retries_persisted_jobs(
    authenticated_client: TestClient, session: Session
) -> None:
    now = datetime(2030, 5, 1, 12, tzinfo=UTC)
    profile, _ = _team_and_fixture(session, now + timedelta(days=1))
    service = SchedulerService()
    service.schedule_team_fixtures(session, profile.id, now)
    job = session.scalar(select(GenerationJob))
    assert job is not None
    job.status = FAILED
    session.commit()

    listed = authenticated_client.get("/api/v1/jobs")
    retried = authenticated_client.post(f"/api/v1/jobs/{job.id}/retry")

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == str(job.id)
    assert retried.status_code == 200
    assert retried.json()["status"] == "PENDING"
