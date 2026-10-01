from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_content_review import _pack

from app.domain.models import User
from app.schemas.performance import ContentPerformanceCreate
from app.services.auth import hash_password
from app.services.content_performance import ContentPerformanceService


def test_manual_performance_snapshots_are_persisted_and_ordered(session: Session) -> None:
    pack = _pack(session)
    service = ContentPerformanceService()
    earlier = datetime(2030, 1, 1, tzinfo=UTC)
    later = datetime(2030, 1, 2, tzinfo=UTC)
    first = service.record(
        session,
        pack.id,
        ContentPerformanceCreate(
            platform="TikTok",
            views=1000,
            likes=80,
            comments=10,
            shares=5,
            average_percentage_viewed=72.5,
            measured_at=earlier,
        ),
    )
    second = service.record(
        session,
        pack.id,
        ContentPerformanceCreate(platform="TikTok", views=1500, measured_at=later),
    )

    measurements = service.list(session, pack.id)
    assert first.platform == "tiktok"
    assert [item.id for item in measurements] == [second.id, first.id]
    assert measurements[0].source == "manual"


def test_performance_requires_an_existing_content_pack(session: Session) -> None:
    with pytest.raises(LookupError):
        ContentPerformanceService().record(
            session,
            uuid4(),
            ContentPerformanceCreate(platform="youtube", views=1),
        )


def test_performance_api_requires_a_session_and_returns_manual_snapshot(
    client: TestClient, session: Session
) -> None:
    user = User(email="performance@example.com", password_hash=hash_password("secure-password"))
    session.add(user)
    session.commit()
    pack = _pack(session)

    denied = client.post(f"/api/v1/contents/{pack.id}/performance", json={"platform": "tiktok"})
    client.post(
        "/api/v1/auth/login",
        json={"email": "performance@example.com", "password": "secure-password"},
    )
    created = client.post(
        f"/api/v1/contents/{pack.id}/performance",
        json={"platform": "tiktok", "views": 250, "likes": 12},
    )
    listed = client.get(f"/api/v1/contents/{pack.id}/performance")

    assert denied.status_code == 401
    assert created.status_code == 200
    assert created.json()["source"] == "manual"
    assert listed.status_code == 200
    assert listed.json()[0]["views"] == 250
