from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.models import User
from app.schemas.jobs import GenerationJobRead
from app.services.scheduler import SchedulerService

router = APIRouter()
service = SchedulerService()


@router.get("/jobs", response_model=list[GenerationJobRead])
def list_jobs(
    status: str | None = None, session: Session = Depends(get_db_session)
) -> list[GenerationJobRead]:
    return [GenerationJobRead.model_validate(job) for job in service.list_jobs(session, status)]


@router.post("/jobs/{job_id}/retry", response_model=GenerationJobRead)
def retry_job(
    job_id: UUID,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> GenerationJobRead:
    try:
        return GenerationJobRead.model_validate(service.retry_job(session, job_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail="Generation job not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
