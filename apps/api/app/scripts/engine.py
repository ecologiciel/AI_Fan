from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.editorial.types import EditorialPackage
from app.prompts.script import build_repair_request, build_script_request
from app.providers.llm.protocol import LLMProvider
from app.scripts.schemas import FactValidationResult, ScriptDraft
from app.scripts.validator import FactValidator


@dataclass(frozen=True)
class ScriptGenerationResult:
    draft: ScriptDraft
    validation: FactValidationResult
    attempts: int


class ScriptEngine:
    def __init__(self, provider: LLMProvider, validator: FactValidator | None = None) -> None:
        self._provider = provider
        self._validator = validator or FactValidator()

    async def generate(
        self,
        package: EditorialPackage,
        evidence_manifest: list[dict[str, Any]],
        recent_summary: list[dict[str, Any]],
    ) -> ScriptGenerationResult:
        request = build_script_request(package, evidence_manifest, recent_summary)
        draft = await self._provider.generate_structured(request, ScriptDraft)
        validation = self._validator.validate(package, evidence_manifest, draft)
        if validation.valid:
            return ScriptGenerationResult(draft, validation, 1)
        repair = build_repair_request(
            package, evidence_manifest, draft.model_dump(), validation.issues
        )
        corrected = await self._provider.generate_structured(repair, ScriptDraft)
        corrected_validation = self._validator.validate(package, evidence_manifest, corrected)
        return ScriptGenerationResult(corrected, corrected_validation, 2)
