from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContentPerformanceCreate(BaseModel):
    platform: str = Field(min_length=2, max_length=40)
    published_at: datetime | None = None
    views: int = Field(default=0, ge=0)
    engaged_views: int | None = Field(default=None, ge=0)
    average_watch_seconds: float | None = Field(default=None, ge=0)
    average_percentage_viewed: float | None = Field(default=None, ge=0, le=100)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)
    saves: int | None = Field(default=None, ge=0)
    followers_gained: int | None = Field(default=None, ge=0)
    measured_at: datetime | None = None
    source: Literal["manual"] = "manual"


class ContentPerformanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_pack_id: UUID
    platform: str
    published_at: datetime | None
    views: int
    engaged_views: int | None
    average_watch_seconds: float | None
    average_percentage_viewed: float | None
    likes: int
    comments: int
    shares: int
    saves: int | None
    followers_gained: int | None
    measured_at: datetime
    source: str
    created_at: datetime
