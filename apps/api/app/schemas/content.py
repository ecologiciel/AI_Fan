from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ContentPackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_profile_id: UUID
    fixture_id: UUID
    generation_job_id: UUID | None
    content_type: Literal["PRE_MATCH", "POST_MATCH"]
    revision_number: int
    team_profile_version: int
    revised_from_id: UUID | None
    revision_reason: str | None
    status: str
    language: str
    target_duration_seconds: int
    target_word_count: int
    estimated_duration_seconds: int
    emotion: dict[str, Any]
    narrative_angle: dict[str, Any]
    selected_insights: list[Any]
    hooks: list[Any]
    recommended_hook: str | None
    title: str | None
    first_screen_text: str | None
    script: str | None
    segments: list[Any]
    caption: str | None
    comment_question: str | None
    hashtags: list[Any]
    editorial_tags: dict[str, Any]
    evidence_manifest: list[Any]
    quality_checks: dict[str, Any]
    quality_warning: bool
    prompt_version: str
    llm_provider: str | None
    llm_model: str | None
    reviewed_at: datetime | None
    reviewed_by_id: UUID | None
    review_note: str | None
    approved_at: datetime | None
    approved_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ContentReviewRequest(BaseModel):
    note: str | None = None


class ContentRejectRequest(BaseModel):
    reason: str


class ContentEditRequest(BaseModel):
    title: str | None = None
    first_screen_text: str | None = None
    script: str | None = None
    caption: str | None = None
    comment_question: str | None = None
    recommended_hook: str | None = None
    revision_reason: str = "MANUAL_EDIT"
