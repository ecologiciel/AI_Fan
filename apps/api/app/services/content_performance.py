from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ContentPack, ContentPerformance
from app.schemas.performance import ContentPerformanceCreate


class ContentPerformanceService:
    """Append-only manual performance measurements, deliberately without recommendation logic."""

    def record(
        self, session: Session, content_pack_id: UUID, payload: ContentPerformanceCreate
    ) -> ContentPerformance:
        if session.get(ContentPack, content_pack_id) is None:
            raise LookupError("Content pack not found")
        measurement = ContentPerformance(
            content_pack_id=content_pack_id,
            platform=payload.platform.strip().lower(),
            published_at=payload.published_at,
            views=payload.views,
            engaged_views=payload.engaged_views,
            average_watch_seconds=payload.average_watch_seconds,
            average_percentage_viewed=payload.average_percentage_viewed,
            likes=payload.likes,
            comments=payload.comments,
            shares=payload.shares,
            saves=payload.saves,
            followers_gained=payload.followers_gained,
            measured_at=payload.measured_at or datetime.now(UTC),
            source=payload.source,
        )
        session.add(measurement)
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise
        session.refresh(measurement)
        return measurement

    @staticmethod
    def list(session: Session, content_pack_id: UUID) -> list[ContentPerformance]:
        if session.get(ContentPack, content_pack_id) is None:
            raise LookupError("Content pack not found")
        return list(
            session.scalars(
                select(ContentPerformance)
                .where(ContentPerformance.content_pack_id == content_pack_id)
                .order_by(ContentPerformance.measured_at.desc())
            )
        )
