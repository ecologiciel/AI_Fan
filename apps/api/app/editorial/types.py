from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class CharacterContext:
    language: str
    locale: str
    identity: str
    tone: dict[str, int]
    speech_rules: list[str]
    cultural_context: dict[str, Any]


@dataclass(frozen=True)
class EmotionContext:
    primary: str
    secondary: str
    intensity: int
    confidence: int
    rivalry: int
    arc: list[str]


@dataclass(frozen=True)
class NarrativeAngle:
    code: str
    rationale: str


@dataclass(frozen=True)
class DurationContext:
    target_duration_seconds: int
    target_word_count: int
    minimum_word_count: int
    maximum_word_count: int
    mode: str


@dataclass(frozen=True)
class EditorialInsight:
    id: UUID
    insight_type: str
    claim: str
    evidence: list[Any]
    final_score: int
    confidence_score: float


@dataclass(frozen=True)
class EditorialPackage:
    fixture_id: UUID
    team_profile_id: UUID
    content_type: str
    language: str
    match: dict[str, Any]
    character: CharacterContext
    emotion: EmotionContext
    narrative_angle: NarrativeAngle
    duration: DurationContext
    insights: list[EditorialInsight]
    ready_for_script: bool
    readiness_reason: str | None
