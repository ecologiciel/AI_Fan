from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Slug = str


class TeamProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Slug = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    display_name: str = Field(min_length=1, max_length=160)
    short_name: str = Field(min_length=1, max_length=80)
    active: bool = True
    football_provider: str = Field(default="sportmonks", min_length=1, max_length=80)
    external_team_id: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    primary_script_language: str = Field(min_length=2, max_length=16)
    locale: str = Field(min_length=2, max_length=16)
    cultural_context: dict[str, Any] = Field(default_factory=dict)
    fan_identity: str = Field(min_length=1, max_length=240)
    character_name: str | None = Field(default=None, max_length=120)
    character_description: str | None = None
    speech_style: str | None = None
    speech_rate_wpm: int = Field(default=150, ge=80, le=250)
    default_duration_mode: str = Field(default="AUTO", pattern=r"^(AUTO|30|45|60|90)$")
    forced_duration_seconds: int | None = Field(default=None, ge=1, le=600)
    prematch_offset_minutes: int = Field(default=360, ge=0, le=10080)
    postmatch_delay_minutes: int = Field(default=10, ge=0, le=1440)
    validation_mode: str = Field(default="HUMAN_REQUIRED", min_length=1, max_length=32)
    emotion_base_level: int = Field(default=50, ge=0, le=100)
    provocation_level: int = Field(default=50, ge=0, le=100)
    humor_level: int = Field(default=50, ge=0, le=100)
    technical_depth: int = Field(default=50, ge=0, le=100)
    rivalry_boost: int = Field(default=0, ge=0, le=100)
    optimism_bias: int = Field(default=50, ge=0, le=100)
    self_criticism_level: int = Field(default=50, ge=0, le=100)
    allowed_slang: list[str] = Field(default_factory=list)
    forbidden_phrases: list[str] = Field(default_factory=list)
    favorite_expressions: list[str] = Field(default_factory=list)
    editorial_rules: list[str] = Field(default_factory=list)


class TeamProfileCreate(TeamProfileFields):
    pass


class TeamProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    short_name: str | None = Field(default=None, min_length=1, max_length=80)
    active: bool | None = None
    football_provider: str | None = Field(default=None, min_length=1, max_length=80)
    external_team_id: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)
    primary_script_language: str | None = Field(default=None, min_length=2, max_length=16)
    locale: str | None = Field(default=None, min_length=2, max_length=16)
    cultural_context: dict[str, Any] | None = None
    fan_identity: str | None = Field(default=None, min_length=1, max_length=240)
    character_name: str | None = Field(default=None, max_length=120)
    character_description: str | None = None
    speech_style: str | None = None
    speech_rate_wpm: int | None = Field(default=None, ge=80, le=250)
    default_duration_mode: str | None = Field(default=None, pattern=r"^(AUTO|30|45|60|90)$")
    forced_duration_seconds: int | None = Field(default=None, ge=1, le=600)
    prematch_offset_minutes: int | None = Field(default=None, ge=0, le=10080)
    postmatch_delay_minutes: int | None = Field(default=None, ge=0, le=1440)
    validation_mode: str | None = Field(default=None, min_length=1, max_length=32)
    emotion_base_level: int | None = Field(default=None, ge=0, le=100)
    provocation_level: int | None = Field(default=None, ge=0, le=100)
    humor_level: int | None = Field(default=None, ge=0, le=100)
    technical_depth: int | None = Field(default=None, ge=0, le=100)
    rivalry_boost: int | None = Field(default=None, ge=0, le=100)
    optimism_bias: int | None = Field(default=None, ge=0, le=100)
    self_criticism_level: int | None = Field(default=None, ge=0, le=100)
    allowed_slang: list[str] | None = None
    forbidden_phrases: list[str] | None = None
    favorite_expressions: list[str] | None = None
    editorial_rules: list[str] | None = None


class TeamProfileRead(TeamProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    profile_version: int
    created_at: datetime
    updated_at: datetime


class TeamDuplicateRequest(BaseModel):
    slug: Slug = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    short_name: str | None = Field(default=None, min_length=1, max_length=80)


class TeamRivalryCreate(BaseModel):
    opponent_external_team_id: str = Field(min_length=1, max_length=120)
    opponent_name: str = Field(min_length=1, max_length=160)
    intensity: int = Field(ge=0, le=100)
    rivalry_label: str | None = Field(default=None, max_length=160)
    custom_character_rules: dict[str, Any] = Field(default_factory=dict)


class TeamRivalryUpdate(BaseModel):
    opponent_external_team_id: str | None = Field(default=None, min_length=1, max_length=120)
    opponent_name: str | None = Field(default=None, min_length=1, max_length=160)
    intensity: int | None = Field(default=None, ge=0, le=100)
    rivalry_label: str | None = Field(default=None, max_length=160)
    custom_character_rules: dict[str, Any] | None = None


class TeamRivalryRead(TeamRivalryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_profile_id: UUID
