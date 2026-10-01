from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models import ContentPack, GenerationJob, TeamProfile
from app.editorial.types import EditorialPackage
from app.prompts.script import build_evidence_manifest, prompt_version_for
from app.providers.llm.protocol import LLMProvider
from app.scripts.engine import ScriptEngine
from app.scripts.schemas import ScriptSegmentDraft
from app.services.editorial_context import EditorialContextService


class ContentPackService:
    """Turns one deterministic editorial package into an auditable human-review item."""

    def __init__(self, provider: LLMProvider) -> None:
        self._context = EditorialContextService()
        self._engine = ScriptEngine(provider)
        self._provider = provider

    async def generate(
        self,
        session: Session,
        fixture_id: UUID,
        team_profile_id: UUID,
        content_type: str,
        generation_job: GenerationJob | None = None,
    ) -> ContentPack:
        if generation_job:
            existing = session.scalar(
                select(ContentPack).where(ContentPack.generation_job_id == generation_job.id)
            )
            if existing:
                return existing
        package = self._context.build(session, fixture_id, team_profile_id, content_type)
        evidence_manifest = build_evidence_manifest(package)
        revision = self._next_revision(session, fixture_id, team_profile_id, content_type)
        common = self._common_values(session, package, evidence_manifest, revision, generation_job)
        if not package.ready_for_script:
            pack = ContentPack(
                **common,
                quality_warning=True,
                quality_checks={"facts_validated": False, "reason": package.readiness_reason},
            )
        else:
            result = await self._engine.generate(
                package, evidence_manifest, self._recent_summary(session, team_profile_id)
            )
            draft = result.draft
            pack = ContentPack(
                **common,
                estimated_duration_seconds=round(
                    result.validation.word_count
                    * package.duration.target_duration_seconds
                    / package.duration.target_word_count
                ),
                hooks=[hook.model_dump() for hook in draft.hooks],
                recommended_hook=draft.hooks[draft.recommended_hook_index].text
                if draft.hooks and 0 <= draft.recommended_hook_index < len(draft.hooks)
                else None,
                title=draft.title,
                first_screen_text=draft.first_screen_text,
                script=draft.script,
                segments=self._segments_with_timing(
                    draft.segments, package.duration.target_duration_seconds
                ),
                caption=draft.caption,
                comment_question=draft.comment_question,
                hashtags=draft.hashtags,
                quality_warning=not result.validation.valid,
                quality_checks={
                    "facts_validated": result.validation.valid,
                    "word_count_valid": "WORD_COUNT_OUT_OF_RANGE" not in result.validation.issues,
                    "language_valid": not any(
                        issue in result.validation.issues
                        for issue in ("LANGUAGE_MISMATCH", "LANGUAGE_CONTENT_MISMATCH")
                    ),
                    "duplicate_content_check": True,
                    "validation_issues": result.validation.issues,
                    "generation_attempts": result.attempts,
                },
                original_generated_payload=draft.model_dump(),
            )
            if draft.hooks and 0 <= draft.recommended_hook_index < len(draft.hooks):
                pack.editorial_tags["hook_type"] = draft.hooks[draft.recommended_hook_index].type
        session.add(pack)
        session.commit()
        session.refresh(pack)
        return pack

    def list_packs(self, session: Session, status: str | None = None) -> list[ContentPack]:
        statement = select(ContentPack).order_by(ContentPack.created_at.desc())
        if status:
            statement = statement.where(ContentPack.status == status)
        return list(session.scalars(statement))

    @staticmethod
    def get(session: Session, content_id: UUID) -> ContentPack:
        pack = session.get(ContentPack, content_id)
        if pack is None:
            raise LookupError("Content pack not found")
        return pack

    def _common_values(
        self,
        session: Session,
        package: EditorialPackage,
        manifest: list[dict[str, Any]],
        revision: int,
        job: GenerationJob | None,
    ) -> dict[str, Any]:
        return {
            "team_profile_id": package.team_profile_id,
            "team_profile_version": self._profile_version(session, package.team_profile_id),
            "fixture_id": package.fixture_id,
            "generation_job_id": job.id if job else None,
            "content_type": package.content_type,
            "revision_number": revision,
            "status": "NEEDS_REVIEW",
            "language": package.language,
            "target_duration_seconds": package.duration.target_duration_seconds,
            "target_word_count": package.duration.target_word_count,
            "emotion": asdict(package.emotion),
            "narrative_angle": asdict(package.narrative_angle),
            "editorial_tags": self._editorial_tags(package, manifest),
            "selected_insights": [
                {
                    "id": str(item.id),
                    "type": item.insight_type,
                    "claim": item.claim,
                    "final_score": item.final_score,
                }
                for item in package.insights
            ],
            "evidence_manifest": manifest,
            "prompt_version": prompt_version_for(package.content_type),
            "llm_provider": self._provider.name,
            "llm_model": self._provider.model,
        }

    @staticmethod
    def _profile_version(session: Session, team_profile_id: UUID) -> int:
        profile = session.get(TeamProfile, team_profile_id)
        if profile is None:
            raise LookupError("Team profile not found")
        return profile.profile_version

    @staticmethod
    def _editorial_tags(
        package: EditorialPackage, evidence_manifest: list[dict[str, Any]]
    ) -> dict[str, Any]:
        featured_players = sorted(
            {
                str(item["player_name"])
                for item in evidence_manifest
                if isinstance(item.get("player_name"), str)
            }
        )
        return {
            "hook_type": None,
            "narrative_angle": package.narrative_angle.code,
            "insight_types": [item.insight_type for item in package.insights],
            "duration_seconds": package.duration.target_duration_seconds,
            "emotion_intensity": package.emotion.intensity,
            "rivalry_intensity": package.emotion.rivalry,
            "featured_players": featured_players,
        }

    @staticmethod
    def _next_revision(session: Session, fixture_id: UUID, team_id: UUID, content_type: str) -> int:
        current = session.scalar(
            select(func.max(ContentPack.revision_number)).where(
                ContentPack.fixture_id == fixture_id,
                ContentPack.team_profile_id == team_id,
                ContentPack.content_type == content_type,
            )
        )
        return int(current or 0) + 1

    @staticmethod
    def _recent_summary(session: Session, team_id: UUID) -> list[dict[str, Any]]:
        recent = list(
            session.scalars(
                select(ContentPack)
                .where(ContentPack.team_profile_id == team_id)
                .order_by(ContentPack.created_at.desc())
                .limit(10)
            )
        )
        return [
            {
                "hooks": [item.get("text") for item in pack.hooks[:1]],
                "narrative_angle": pack.narrative_angle.get("code"),
            }
            for pack in recent
        ]

    @staticmethod
    def _segments_with_timing(
        segments: list[ScriptSegmentDraft], duration: int
    ) -> list[dict[str, Any]]:
        if not segments:
            return []
        weights = [max(1, len(item.text.split())) for item in segments]
        total = sum(weights)
        start = 0
        result = []
        for index, (segment, weight) in enumerate(zip(segments, weights, strict=True)):
            end = (
                duration if index == len(segments) - 1 else round(start + duration * weight / total)
            )
            result.append(
                {
                    "start": start,
                    "end": end,
                    "purpose": segment.purpose,
                    "text": segment.text,
                    "evidence_ids": segment.evidence_ids,
                }
            )
            start = end
        return result
