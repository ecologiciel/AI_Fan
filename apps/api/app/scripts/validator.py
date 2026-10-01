from __future__ import annotations

import re
from typing import Any

from app.editorial.types import EditorialPackage
from app.scripts.schemas import FactValidationResult, ScriptDraft

NUMBER_RE = re.compile(r"(?<![\w-])\d+(?:[,.]\d+)?(?![\w-])")
WORD_RE = re.compile(r"\b[\wÀ-ÿ]+(?:['’][\wÀ-ÿ]+)?\b", re.UNICODE)


class FactValidator:
    """Deterministic guardrail: the LLM never authorizes a new fact."""

    def validate(
        self, package: EditorialPackage, evidence_manifest: list[dict[str, Any]], draft: ScriptDraft
    ) -> FactValidationResult:
        issues: list[str] = []
        word_count = len(WORD_RE.findall(draft.script))
        if draft.language.lower() != package.language.lower():
            issues.append("LANGUAGE_MISMATCH")
        if not _looks_like_requested_language(draft.script, package.language):
            issues.append("LANGUAGE_CONTENT_MISMATCH")
        if (
            not package.duration.minimum_word_count
            <= word_count
            <= package.duration.maximum_word_count
        ):
            issues.append("WORD_COUNT_OUT_OF_RANGE")
        categories = {hook.type.lower() for hook in draft.hooks}
        if len(draft.hooks) < 3 or not {"curiosity", "emotion", "contrarian"}.issubset(categories):
            issues.append("INSUFFICIENT_HOOK_DIVERSITY")
        if not 0 <= draft.recommended_hook_index < len(draft.hooks):
            issues.append("INVALID_RECOMMENDED_HOOK")

        allowed_ids = {item["evidence_id"] for item in evidence_manifest}
        allowed_numbers = _numbers_from_evidence(evidence_manifest)
        all_texts = [
            draft.script,
            draft.title,
            draft.first_screen_text,
            draft.caption,
            draft.comment_question,
        ]
        all_texts.extend(hook.text for hook in draft.hooks)
        for segment in draft.segments:
            if not set(segment.evidence_ids).issubset(allowed_ids):
                issues.append("UNKNOWN_EVIDENCE_REFERENCE")
            numbers = _numbers_in_text(segment.text)
            if numbers and not segment.evidence_ids:
                issues.append("NUMERIC_SEGMENT_WITHOUT_EVIDENCE")
            all_texts.append(segment.text)
        unknown_numbers = {
            number
            for text in all_texts
            for number in _numbers_in_text(text)
            if number not in allowed_numbers
        }
        if unknown_numbers:
            issues.append("UNSUPPORTED_NUMBERS:" + ",".join(sorted(unknown_numbers)))

        allowed_entities = {str(package.match["team"]), str(package.match["opponent"])}
        allowed_entities.update(_entity_names(evidence_manifest))
        unknown_entities = set(draft.mentioned_entities) - allowed_entities
        if unknown_entities:
            issues.append("UNSUPPORTED_ENTITIES:" + ",".join(sorted(unknown_entities)))
        return FactValidationResult(valid=not issues, issues=issues, word_count=word_count)


def _numbers_in_text(text: str) -> set[str]:
    return {match.group(0).replace(",", ".") for match in NUMBER_RE.finditer(text)}


def _numbers_from_evidence(value: Any) -> set[str]:
    numbers: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            numbers.update(_numbers_from_evidence(item))
    elif isinstance(value, list):
        for item in value:
            numbers.update(_numbers_from_evidence(item))
    elif isinstance(value, int | float) and not isinstance(value, bool):
        number = float(value)
        numbers.add(str(int(number)) if number.is_integer() else str(number))
    return numbers


def _entity_names(evidence_manifest: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for item in evidence_manifest:
        for key in ("player_name", "team_name", "opponent_name"):
            if isinstance(item.get(key), str):
                names.add(item[key])
    return names


def _looks_like_requested_language(text: str, language: str) -> bool:
    """Small deterministic sanity check; the profile code remains the language authority."""
    if language.lower() != "es":
        return True
    tokens = {token.lower() for token in WORD_RE.findall(text)}
    return bool(
        tokens
        & {"el", "la", "los", "las", "que", "de", "y", "en", "con", "para", "es", "un", "una"}
    )
