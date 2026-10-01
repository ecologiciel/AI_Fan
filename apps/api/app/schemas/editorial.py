from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class CharacterContextRead(BaseModel):
    language: str
    locale: str
    identity: str
    tone: dict[str, int]
    speech_rules: list[str]
    cultural_context: dict[str, Any]


class EmotionContextRead(BaseModel):
    primary: str
    secondary: str
    intensity: int
    confidence: int
    rivalry: int
    arc: list[str]


class NarrativeAngleRead(BaseModel):
    code: str
    rationale: str


class DurationContextRead(BaseModel):
    target_duration_seconds: int
    target_word_count: int
    minimum_word_count: int
    maximum_word_count: int
    mode: str


class EditorialInsightRead(BaseModel):
    id: UUID
    insight_type: str
    claim: str
    evidence: list[Any]
    final_score: int
    confidence_score: float


class EditorialPackageRead(BaseModel):
    fixture_id: UUID
    team_profile_id: UUID
    content_type: Literal["PRE_MATCH", "POST_MATCH"]
    language: str
    match: dict[str, Any]
    character: CharacterContextRead
    emotion: EmotionContextRead
    narrative_angle: NarrativeAngleRead
    duration: DurationContextRead
    insights: list[EditorialInsightRead]
    ready_for_script: bool
    readiness_reason: str | None
