import asyncio
from uuid import uuid4

from app.editorial.types import (
    CharacterContext,
    DurationContext,
    EditorialPackage,
    EmotionContext,
    NarrativeAngle,
)
from app.providers.llm.models import LLMGenerationRequest
from app.scripts.engine import ScriptEngine
from app.scripts.schemas import ScriptDraft
from app.scripts.validator import FactValidator


def _package() -> EditorialPackage:
    return EditorialPackage(
        fixture_id=uuid4(),
        team_profile_id=uuid4(),
        content_type="POST_MATCH",
        language="es",
        match={"team": "FC Barcelona", "opponent": "Opponent", "score": {"team": 1, "opponent": 0}},
        character=CharacterContext("es", "es-ES", "native Catalan supporter", {}, [], {}),
        emotion=EmotionContext("euphoric", "analytical", 70, 90, 0, []),
        narrative_angle=NarrativeAngle("STRAIGHT_ANALYSIS", "test"),
        duration=DurationContext(30, 10, 4, 100, "AUTO"),
        insights=[],
        ready_for_script=True,
        readiness_reason=None,
    )


def _draft(number: str) -> dict[str, object]:
    return {
        "language": "es",
        "hooks": [
            {"type": "curiosity", "text": "Hay un dato que importa."},
            {"type": "emotion", "text": "Esto se vive de verdad."},
            {"type": "contrarian", "text": "El marcador no basta."},
        ],
        "recommended_hook_index": 0,
        "title": "Análisis del Barça",
        "first_screen_text": "Una prueba clara",
        "script": f"El Barça cerró el partido con {number} de valor respaldado por la prueba.",
        "segments": [
            {"purpose": "hook", "text": f"El Barça tuvo {number}.", "evidence_ids": ["EV-01"]}
        ],
        "caption": "Análisis con prueba.",
        "comment_question": "¿Qué viste tú?",
        "hashtags": ["#Barça"],
        "mentioned_entities": ["FC Barcelona"],
    }


class FakeLLMProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.requests: list[LLMGenerationRequest] = []

    async def generate_structured(
        self, request: LLMGenerationRequest, response_schema: type[ScriptDraft]
    ) -> ScriptDraft:
        self.requests.append(request)
        payload = _draft("99" if len(self.requests) == 1 else "1.5")
        return response_schema.model_validate(payload)


def test_validator_rejects_a_number_absent_from_evidence() -> None:
    result = FactValidator().validate(
        _package(),
        [{"evidence_id": "EV-01", "current": 1.5}],
        ScriptDraft.model_validate(_draft("99")),
    )

    assert result.valid is False
    assert "UNSUPPORTED_NUMBERS:99" in result.issues


def test_validator_rejects_an_entity_absent_from_the_match_and_evidence() -> None:
    draft = ScriptDraft.model_validate(_draft("1.5"))
    draft.mentioned_entities = ["Invented Player"]

    result = FactValidator().validate(_package(), [{"evidence_id": "EV-01", "current": 1.5}], draft)

    assert result.valid is False
    assert "UNSUPPORTED_ENTITIES:Invented Player" in result.issues


def test_script_engine_attempts_one_fact_repair_and_accepts_corrected_draft() -> None:
    provider = FakeLLMProvider()

    result = asyncio.run(
        ScriptEngine(provider).generate(_package(), [{"evidence_id": "EV-01", "current": 1.5}], [])
    )

    assert result.validation.valid is True
    assert result.attempts == 2
    assert len(provider.requests) == 2
    assert provider.requests[0].prompt_version == "postmatch_script_v1"
    assert provider.requests[1].prompt_version == "fact_repair_v1"
