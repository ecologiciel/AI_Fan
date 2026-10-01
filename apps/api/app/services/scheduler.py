from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.models import Fixture, GenerationJob, TeamFixtureLink, TeamProfile

PRE_MATCH = "PRE_MATCH"
POST_MATCH = "POST_MATCH"
PENDING = "PENDING"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"
SKIPPED = "SKIPPED"
FINAL_FIXTURE_STATUSES = {"FINISHED"}
NON_PLAYABLE_FIXTURE_STATUSES = {"POSTPONED", "CANCELLED", "ABANDONED"}
POSTMATCH_DATA_RETRY_SECONDS = 10 * 60
logger = logging.getLogger(__name__)


class GenerationPipelineUnavailable(Exception):
    """Raised while the scheduler exists before the generation pipeline phase."""


class PostMatchDataPending(Exception):
    """A just-finished fixture has no usable team statistics yet."""


class GenerationJobExecutor(Protocol):
    async def execute(self, job: GenerationJob) -> None: ...


@dataclass(frozen=True)
class ScheduleResult:
    created: int
    rescheduled: int
    cancelled: int


def build_idempotency_key(
    team_profile_id: UUID, fixture_id: UUID, content_type: str, profile_version: int
) -> str:
    return f"{team_profile_id}:{fixture_id}:{content_type}:v{profile_version}"


class SchedulerService:
    """Persistent scheduling, planning and atomic claiming of automatic generation jobs."""

    def schedule_team_fixtures(
        self, session: Session, team_id: UUID, now: datetime | None = None
    ) -> ScheduleResult:
        now = now or datetime.now(UTC)
        profile = self._get_profile(session, team_id)
        fixtures = list(
            session.scalars(
                select(Fixture)
                .join(TeamFixtureLink)
                .where(TeamFixtureLink.team_profile_id == team_id)
                .order_by(Fixture.kickoff_at)
            )
        )
        created = rescheduled = cancelled = 0
        for fixture in fixtures:
            result = self.schedule_fixture(session, profile, fixture, now)
            created += result.created
            rescheduled += result.rescheduled
            cancelled += result.cancelled
        session.commit()
        return ScheduleResult(created, rescheduled, cancelled)

    def schedule_fixture(
        self, session: Session, profile: TeamProfile, fixture: Fixture, now: datetime
    ) -> ScheduleResult:
        now = _as_utc(now)
        kickoff_at = _as_utc(fixture.kickoff_at)
        if not profile.active or fixture.status in NON_PLAYABLE_FIXTURE_STATUSES:
            return ScheduleResult(0, 0, self._cancel_pending_jobs(session, profile.id, fixture.id))

        created = rescheduled = cancelled = 0
        if fixture.status == "SCHEDULED" and kickoff_at > now:
            result = self._ensure_automatic_job(
                session,
                profile,
                fixture,
                PRE_MATCH,
                kickoff_at - timedelta(minutes=profile.prematch_offset_minutes),
                update_schedule=True,
            )
            created += result.created
            rescheduled += result.rescheduled
            cancelled += result.cancelled
        elif fixture.status != "SCHEDULED":
            cancelled += self._cancel_pending_jobs(session, profile.id, fixture.id, PRE_MATCH)

        if fixture.status in FINAL_FIXTURE_STATUSES:
            detected_at = (
                _as_utc(fixture.last_provider_sync_at) if fixture.last_provider_sync_at else now
            )
            result = self._ensure_automatic_job(
                session,
                profile,
                fixture,
                POST_MATCH,
                detected_at + timedelta(minutes=profile.postmatch_delay_minutes),
                update_schedule=False,
            )
            created += result.created
            rescheduled += result.rescheduled
            cancelled += result.cancelled
        return ScheduleResult(created, rescheduled, cancelled)

    def claim_due_jobs(
        self, session: Session, now: datetime | None = None, limit: int = 10
    ) -> list[GenerationJob]:
        now = now or datetime.now(UTC)
        statement = (
            select(GenerationJob)
            .where(
                GenerationJob.status == PENDING,
                GenerationJob.scheduled_for <= now,
                GenerationJob.attempt_count < GenerationJob.max_attempts,
            )
            .order_by(GenerationJob.scheduled_for)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(session.scalars(statement))
        for job in jobs:
            job.status = RUNNING
            job.started_at = now
            job.attempt_count += 1
            job.last_error = None
        session.commit()
        return jobs

    async def dispatch_due_jobs(
        self,
        session: Session,
        executor: GenerationJobExecutor,
        now: datetime | None = None,
        limit: int = 10,
    ) -> list[GenerationJob]:
        dispatch_at = now or datetime.now(UTC)
        claimed = self.claim_due_jobs(session, dispatch_at, limit)
        for job in claimed:
            started = perf_counter()
            try:
                await executor.execute(job)
            except PostMatchDataPending as error:
                status = self._retry_postmatch_data_once(session, job, str(error), dispatch_at)
            except GenerationPipelineUnavailable as error:
                self._finish_job(session, job, SKIPPED, str(error))
                status = SKIPPED
            except Exception as error:  # noqa: BLE001 - external execution must fail safely
                status = self._retry_or_finish_job(session, job, str(error), dispatch_at)
            else:
                self._finish_job(session, job, SUCCEEDED)
                status = SUCCEEDED
            profile = session.get(TeamProfile, job.team_profile_id)
            logger.info(
                "generation_job_completed",
                extra={
                    "job_id": str(job.id),
                    "team_profile_id": str(job.team_profile_id),
                    "fixture_id": str(job.fixture_id),
                    "content_type": job.content_type,
                    "provider": profile.football_provider if profile else None,
                    "duration_ms": round((perf_counter() - started) * 1000),
                    "status": status,
                    "error_type": None if status == SUCCEEDED else "generation_error",
                },
            )
        return claimed

    def retry_job(
        self, session: Session, job_id: UUID, now: datetime | None = None
    ) -> GenerationJob:
        job = session.get(GenerationJob, job_id)
        if job is None:
            raise LookupError("Generation job not found")
        if job.status not in {FAILED, SKIPPED, CANCELLED}:
            raise ValueError("Only failed, skipped, or cancelled jobs can be retried")
        job.status = PENDING
        job.scheduled_for = now or datetime.now(UTC)
        job.started_at = None
        job.finished_at = None
        job.last_error = None
        job.attempt_count = 0
        session.commit()
        return job

    def list_jobs(self, session: Session, status: str | None = None) -> list[GenerationJob]:
        statement = select(GenerationJob).order_by(GenerationJob.scheduled_for.desc())
        if status:
            statement = statement.where(GenerationJob.status == status)
        return list(session.scalars(statement))

    def _ensure_automatic_job(
        self,
        session: Session,
        profile: TeamProfile,
        fixture: Fixture,
        content_type: str,
        scheduled_for: datetime,
        update_schedule: bool,
    ) -> ScheduleResult:
        idempotency_key = build_idempotency_key(
            profile.id, fixture.id, content_type, profile.profile_version
        )
        stale_jobs = list(
            session.scalars(
                select(GenerationJob).where(
                    GenerationJob.team_profile_id == profile.id,
                    GenerationJob.fixture_id == fixture.id,
                    GenerationJob.content_type == content_type,
                    GenerationJob.idempotency_key != idempotency_key,
                    GenerationJob.status == PENDING,
                )
            )
        )
        for stale_job in stale_jobs:
            stale_job.status = CANCELLED
            stale_job.finished_at = datetime.now(UTC)
            stale_job.last_error = "Superseded by a newer team profile version"

        job = session.scalar(
            select(GenerationJob).where(GenerationJob.idempotency_key == idempotency_key)
        )
        if job is None:
            session.add(
                GenerationJob(
                    team_profile_id=profile.id,
                    fixture_id=fixture.id,
                    content_type=content_type,
                    status=PENDING,
                    scheduled_for=scheduled_for,
                    idempotency_key=idempotency_key,
                    payload={"automatic": True, "team_profile_version": profile.profile_version},
                )
            )
            return ScheduleResult(1, 0, len(stale_jobs))
        if (
            job.status == PENDING
            and update_schedule
            and _as_utc(job.scheduled_for) != scheduled_for
        ):
            job.scheduled_for = scheduled_for
            return ScheduleResult(0, 1, len(stale_jobs))
        return ScheduleResult(0, 0, len(stale_jobs))

    @staticmethod
    def _cancel_pending_jobs(
        session: Session,
        team_profile_id: UUID,
        fixture_id: UUID,
        content_type: str | None = None,
    ) -> int:
        statement = select(GenerationJob).where(
            GenerationJob.team_profile_id == team_profile_id,
            GenerationJob.fixture_id == fixture_id,
            GenerationJob.status == PENDING,
        )
        if content_type:
            statement = statement.where(GenerationJob.content_type == content_type)
        jobs = list(session.scalars(statement))
        for job in jobs:
            job.status = CANCELLED
            job.finished_at = datetime.now(UTC)
            job.last_error = "Fixture is no longer eligible for automatic generation"
        return len(jobs)

    @staticmethod
    def _finish_job(
        session: Session, job: GenerationJob, status: str, error: str | None = None
    ) -> None:
        job.status = status
        job.finished_at = datetime.now(UTC)
        job.last_error = error
        session.commit()

    @staticmethod
    def _retry_or_finish_job(
        session: Session, job: GenerationJob, error: str, now: datetime
    ) -> str:
        """Requeue transient execution failures without creating another job record."""

        if job.attempt_count < job.max_attempts:
            delay_seconds = get_settings().job_retry_base_seconds * (2 ** (job.attempt_count - 1))
            job.status = PENDING
            job.scheduled_for = now + timedelta(seconds=delay_seconds)
            job.finished_at = None
            job.last_error = error
            session.commit()
            return PENDING
        SchedulerService._finish_job(session, job, FAILED, error)
        return FAILED

    @staticmethod
    def _retry_postmatch_data_once(
        session: Session, job: GenerationJob, error: str, now: datetime
    ) -> str:
        """Allow one ten-minute grace period for a provider's final statistics feed."""

        retries = int(job.payload.get("postmatch_data_retry_count", 0))
        if retries >= 1:
            SchedulerService._finish_job(session, job, FAILED, error)
            return FAILED
        payload = dict(job.payload)
        payload["postmatch_data_retry_count"] = retries + 1
        job.payload = payload
        job.status = PENDING
        job.scheduled_for = now + timedelta(seconds=POSTMATCH_DATA_RETRY_SECONDS)
        job.finished_at = None
        job.last_error = error
        session.commit()
        return PENDING

    @staticmethod
    def _get_profile(session: Session, team_id: UUID) -> TeamProfile:
        profile = session.get(TeamProfile, team_id)
        if profile is None:
            raise LookupError("Team profile not found")
        return profile


def _as_utc(value: datetime) -> datetime:
    """Normalize SQLite test values and enforce UTC application semantics."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
