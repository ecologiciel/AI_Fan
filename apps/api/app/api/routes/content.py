from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.domain.models import User
from app.providers.llm.models import LLMProviderError
from app.providers.llm.protocol import LLMProvider
from app.providers.llm.registry import get_llm_provider
from app.schemas.content import (
    ContentEditRequest,
    ContentPackRead,
    ContentRejectRequest,
    ContentReviewRequest,
)
from app.schemas.performance import ContentPerformanceCreate, ContentPerformanceRead
from app.services.content_packs import ContentPackService
from app.services.content_performance import ContentPerformanceService
from app.services.content_review import ContentReviewService

router = APIRouter()
review_service = ContentReviewService()
performance_service = ContentPerformanceService()


@router.get("/contents", response_model=list[ContentPackRead])
def list_contents(
    status: str | None = None,
    session: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
    _: User = Depends(get_current_user),
) -> list[ContentPackRead]:
    return [
        ContentPackRead.model_validate(item)
        for item in ContentPackService(provider).list_packs(session, status)
    ]


@router.get("/contents/{content_id}", response_model=ContentPackRead)
def get_content(
    content_id: UUID,
    session: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
    _: User = Depends(get_current_user),
) -> ContentPackRead:
    try:
        return ContentPackRead.model_validate(ContentPackService(provider).get(session, content_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/fixtures/{fixture_id}/generate/{content_type}", response_model=ContentPackRead)
async def generate_content(
    fixture_id: UUID,
    content_type: Literal["pre-match", "post-match"],
    team_id: UUID,
    session: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
    _: User = Depends(get_current_user),
) -> ContentPackRead:
    internal_type = "PRE_MATCH" if content_type == "pre-match" else "POST_MATCH"
    try:
        pack = await ContentPackService(provider).generate(
            session, fixture_id, team_id, internal_type
        )
        return ContentPackRead.model_validate(pack)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/contents/{content_id}/approve", response_model=ContentPackRead)
def approve_content(
    content_id: UUID,
    payload: ContentReviewRequest,
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ContentPackRead:
    try:
        return ContentPackRead.model_validate(
            review_service.approve(session, content_id, user, payload.note)
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/contents/{content_id}/reject", response_model=ContentPackRead)
def reject_content(
    content_id: UUID,
    payload: ContentRejectRequest,
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ContentPackRead:
    try:
        return ContentPackRead.model_validate(
            review_service.reject(session, content_id, user, payload.reason)
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/contents/{content_id}/regenerate", response_model=ContentPackRead)
async def regenerate_content(
    content_id: UUID,
    session: Session = Depends(get_db_session),
    provider: LLMProvider = Depends(get_llm_provider),
    user: User = Depends(get_current_user),
) -> ContentPackRead:
    try:
        pack = await review_service.regenerate(
            session, content_id, user, ContentPackService(provider)
        )
        return ContentPackRead.model_validate(pack)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except LLMProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.patch("/contents/{content_id}", response_model=ContentPackRead)
def edit_content(
    content_id: UUID,
    payload: ContentEditRequest,
    session: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ContentPackRead:
    updates = payload.model_dump(exclude={"revision_reason"}, exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="At least one content field is required")
    try:
        return ContentPackRead.model_validate(
            review_service.edit(session, content_id, user, updates, payload.revision_reason)
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/contents/{content_id}/performance", response_model=ContentPerformanceRead)
def record_content_performance(
    content_id: UUID,
    payload: ContentPerformanceCreate,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> ContentPerformanceRead:
    try:
        return ContentPerformanceRead.model_validate(
            performance_service.record(session, content_id, payload)
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 - keep invalid snapshots from corrupting review data
        raise HTTPException(
            status_code=422, detail="Unable to record performance measurement"
        ) from error


@router.get("/contents/{content_id}/performance", response_model=list[ContentPerformanceRead])
def list_content_performance(
    content_id: UUID,
    session: Session = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[ContentPerformanceRead]:
    try:
        return [
            ContentPerformanceRead.model_validate(item)
            for item in performance_service.list(session, content_id)
        ]
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
