from __future__ import annotations

from pydantic import BaseModel, Field


class HookDraft(BaseModel):
    type: str
    text: str


class ScriptSegmentDraft(BaseModel):
    purpose: str
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class ScriptDraft(BaseModel):
    language: str
    hooks: list[HookDraft]
    recommended_hook_index: int
    title: str
    first_screen_text: str
    script: str
    segments: list[ScriptSegmentDraft]
    caption: str
    comment_question: str
    hashtags: list[str] = Field(default_factory=list)
    mentioned_entities: list[str] = Field(default_factory=list)


class FactValidationResult(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)
    word_count: int
