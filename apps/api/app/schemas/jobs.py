from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_profile_id: UUID
    fixture_id: UUID
    content_type: str
    status: str
    scheduled_for: datetime
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    max_attempts: int
    idempotency_key: str
    last_error: str | None
    payload: dict[str, Any]
