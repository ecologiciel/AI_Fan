import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_editorial_context import _complete_fixture

from app.domain.models import ContentPack, GenerationJob
from app.providers.llm.models import LLMGenerationRequest
from app.scripts.schemas import ScriptDraft
from app.services.content_packs import ContentPackService


class SpanishLLMProvider:
    name = "fake"
    model = "fake-model"

    async def generate_structured(
        self, request: LLMGenerationRequest, response_schema: type[ScriptDraft]
    ) -> ScriptDraft:
        words = "El Barça análisis prueba emoción partido afición ".split() * 13
        script = " ".join(words[:75])
        return response_schema.model_validate(
            {
                "language": "es",
                "hooks": [
                    {"type": "curiosity", "text": "Hay una prueba que importa."},
                    {"type": "emotion", "text": "Esto se siente mucho."},
                    {"type": "contrarian", "text": "El marcador no basta."},
                ],
                "recommended_hook_index": 0,
                "title": "Análisis del Barça",
                "first_screen_text": "Prueba y emoción",
                "script": script,
                "segments": [{"purpose": "hook", "text": script, "evidence_ids": []}],
                "caption": "Análisis con pruebas.",
                "comment_question": "¿Cómo lo viviste?",
                "hashtags": ["#Barça"],
                "mentioned_entities": [],
            }
        )


def test_content_pack_is_spanish_evidence_backed_and_idempotent_for_a_job(session: Session) -> None:
    profile, fixture = _complete_fixture(session)
    job = GenerationJob(
        team_profile_id=profile.id,
        fixture_id=fixture.id,
        content_type="POST_MATCH",
        status="RUNNING",
        scheduled_for=datetime.now(UTC),
        idempotency_key="content-pack-test",
    )
    session.add(job)
    session.commit()
    service = ContentPackService(SpanishLLMProvider())

    first = asyncio.run(service.generate(session, fixture.id, profile.id, "POST_MATCH", job))
    second = asyncio.run(service.generate(session, fixture.id, profile.id, "POST_MATCH", job))

    persisted = list(session.scalars(select(ContentPack)))
    assert first.id == second.id
    assert len(persisted) == 1
    assert first.status == "NEEDS_REVIEW"
    assert first.language == "es"
    assert first.evidence_manifest
    assert first.editorial_tags["duration_seconds"] == 30
    assert first.editorial_tags["narrative_angle"] == "SCORE_DOES_NOT_TELL_STORY"
    assert first.quality_checks["facts_validated"] is True
