from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import ContentPack, User
from app.services.content_packs import ContentPackService

NEEDS_REVIEW = "NEEDS_REVIEW"
APPROVED = "APPROVED"
REJECTED = "REJECTED"
ARCHIVED = "ARCHIVED"
NUMBER_RE = re.compile(r"(?<![\w-])\d+(?:[,.]\d+)?(?![\w-])")


class ContentReviewService:
    """State transitions and immutable manual revisions for human content review."""

    def approve(
        self, session: Session, content_id: UUID, reviewer: User, note: str | None
    ) -> ContentPack:
        pack = self._reviewable(session, content_id)
        now = datetime.now(UTC)
        pack.status = APPROVED
        pack.reviewed_at = now
        pack.reviewed_by_id = reviewer.id
        pack.review_note = note
        pack.approved_at = now
        pack.approved_by_id = reviewer.id
        session.commit()
        session.refresh(pack)
        return pack

    def reject(
        self, session: Session, content_id: UUID, reviewer: User, reason: str
    ) -> ContentPack:
        pack = self._reviewable(session, content_id)
        pack.status = REJECTED
        pack.reviewed_at = datetime.now(UTC)
        pack.reviewed_by_id = reviewer.id
        pack.review_note = reason
        session.commit()
        session.refresh(pack)
        return pack

    async def regenerate(
        self,
        session: Session,
        content_id: UUID,
        reviewer: User,
        content_service: ContentPackService,
    ) -> ContentPack:
        source = self.get(session, content_id)
        replacement = await content_service.generate(
            session, source.fixture_id, source.team_profile_id, source.content_type
        )
        self._archive_source(session, source, reviewer, "MANUAL_REGENERATE")
        replacement.revised_from_id = source.id
        replacement.revision_reason = "MANUAL_REGENERATE"
        session.commit()
        session.refresh(replacement)
        return replacement

    def edit(
        self,
        session: Session,
        content_id: UUID,
        reviewer: User,
        updates: dict[str, str | None],
        reason: str,
    ) -> ContentPack:
        source = self.get(session, content_id)
        self._validate_manual_facts(source, updates)
        revision = self._next_revision(session, source)
        pack = ContentPack(
            team_profile_id=source.team_profile_id,
            team_profile_version=source.team_profile_version,
            fixture_id=source.fixture_id,
            content_type=source.content_type,
            revision_number=revision,
            revised_from_id=source.id,
            revision_reason=reason,
            status=NEEDS_REVIEW,
            language=source.language,
            target_duration_seconds=source.target_duration_seconds,
            target_word_count=source.target_word_count,
            estimated_duration_seconds=source.estimated_duration_seconds,
            emotion=dict(source.emotion),
            narrative_angle=dict(source.narrative_angle),
            selected_insights=list(source.selected_insights),
            hooks=list(source.hooks),
            recommended_hook=updates.get("recommended_hook") or source.recommended_hook,
            title=updates.get("title") or source.title,
            first_screen_text=updates.get("first_screen_text") or source.first_screen_text,
            script=updates.get("script") or source.script,
            segments=list(source.segments),
            caption=updates.get("caption") or source.caption,
            comment_question=updates.get("comment_question") or source.comment_question,
            hashtags=list(source.hashtags),
            editorial_tags=dict(source.editorial_tags),
            evidence_manifest=list(source.evidence_manifest),
            quality_checks={**source.quality_checks, "manual_edit": True},
            quality_warning=source.quality_warning,
            prompt_version=source.prompt_version,
            llm_provider=source.llm_provider,
            llm_model=source.llm_model,
            original_generated_payload=source.original_generated_payload,
        )
        self._archive_source(session, source, reviewer, "SUPERSEDED_BY_MANUAL_EDIT")
        session.add(pack)
        session.commit()
        session.refresh(pack)
        return pack

    @staticmethod
    def get(session: Session, content_id: UUID) -> ContentPack:
        pack = session.get(ContentPack, content_id)
        if pack is None:
            raise LookupError("Content pack not found")
        return pack

    @staticmethod
    def _reviewable(session: Session, content_id: UUID) -> ContentPack:
        pack = ContentReviewService.get(session, content_id)
        if pack.status != NEEDS_REVIEW:
            raise ValueError("Only content awaiting review can be reviewed")
        return pack

    @staticmethod
    def _archive_source(session: Session, source: ContentPack, reviewer: User, note: str) -> None:
        source.status = ARCHIVED
        source.reviewed_at = datetime.now(UTC)
        source.reviewed_by_id = reviewer.id
        source.review_note = note

    @staticmethod
    def _next_revision(session: Session, source: ContentPack) -> int:
        current = session.scalar(
            select(func.max(ContentPack.revision_number)).where(
                ContentPack.fixture_id == source.fixture_id,
                ContentPack.team_profile_id == source.team_profile_id,
                ContentPack.content_type == source.content_type,
            )
        )
        return int(current or 0) + 1

    @staticmethod
    def _validate_manual_facts(source: ContentPack, updates: dict[str, str | None]) -> None:
        allowed_numbers = _numbers_from_value(source.evidence_manifest)
        values = [value for value in updates.values() if value]
        present_numbers = {
            match.group(0).replace(",", ".")
            for value in values
            for match in NUMBER_RE.finditer(value)
        }
        unsupported = present_numbers - allowed_numbers
        if unsupported:
            raise ValueError(
                "Manual edit contains unsupported numbers: " + ", ".join(sorted(unsupported))
            )


def _numbers_from_value(value: Any) -> set[str]:
    numbers: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            numbers.update(_numbers_from_value(item))
    elif isinstance(value, list):
        for item in value:
            numbers.update(_numbers_from_value(item))
    elif isinstance(value, int | float) and not isinstance(value, bool):
        normalized = float(value)
        numbers.add(str(int(normalized)) if normalized.is_integer() else str(normalized))
    return numbers
