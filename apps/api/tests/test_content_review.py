import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_editorial_context import _complete_fixture

from app.domain.models import ContentPack, Fixture, TeamProfile, User
from app.services.auth import hash_password
from app.services.content_review import ContentReviewService


def _reviewer(session: Session) -> User:
    user = User(email="reviewer@example.com", password_hash=hash_password("secure-password"))
    session.add(user)
    session.commit()
    return user


def _pack(
    session: Session,
    *,
    status: str = "NEEDS_REVIEW",
    profile: TeamProfile | None = None,
    fixture: Fixture | None = None,
    revision_number: int = 1,
) -> ContentPack:
    if profile is None or fixture is None:
        profile, fixture = _complete_fixture(session)
    pack = ContentPack(
        team_profile_id=profile.id,
        team_profile_version=profile.profile_version,
        fixture_id=fixture.id,
        content_type="POST_MATCH",
        revision_number=revision_number,
        status=status,
        language="es",
        target_duration_seconds=30,
        target_word_count=75,
        estimated_duration_seconds=30,
        emotion={},
        narrative_angle={},
        selected_insights=[],
        hooks=[],
        segments=[],
        hashtags=[],
        evidence_manifest=[{"evidence_id": "EV-1", "current": 1.5}],
        quality_checks={"facts_validated": True},
        prompt_version="postmatch_script_v1",
        script="El Barça tuvo 1.5 de referencia.",
    )
    session.add(pack)
    session.commit()
    session.refresh(pack)
    return pack


def test_approval_and_rejection_are_controlled_and_audited(session: Session) -> None:
    reviewer = _reviewer(session)
    service = ContentReviewService()
    source = _pack(session)
    approved = service.approve(session, source.id, reviewer, "Verified")
    rejected = service.reject(
        session,
        _pack(session, profile=source.team_profile, fixture=source.fixture, revision_number=2).id,
        reviewer,
        "Needs another angle",
    )

    assert approved.status == "APPROVED"
    assert approved.approved_by_id == reviewer.id
    assert approved.approved_at is not None
    assert rejected.status == "REJECTED"
    assert rejected.reviewed_by_id == reviewer.id
    assert rejected.review_note == "Needs another angle"
    with pytest.raises(ValueError):
        service.approve(session, approved.id, reviewer, None)


def test_manual_edit_creates_an_immutable_revision_and_rejects_unsupported_numbers(
    session: Session,
) -> None:
    reviewer = _reviewer(session)
    source = _pack(session)
    service = ContentReviewService()

    with pytest.raises(ValueError, match="unsupported numbers"):
        service.edit(
            session, source.id, reviewer, {"script": "El Barça tuvo 99."}, "MANUAL_REVIEW_EDIT"
        )
    revision = service.edit(
        session,
        source.id,
        reviewer,
        {"script": "El Barça tuvo 1.5 de referencia revisada."},
        "MANUAL_REVIEW_EDIT",
    )

    assert source.status == "ARCHIVED"
    assert revision.status == "NEEDS_REVIEW"
    assert revision.revised_from_id == source.id
    assert revision.revision_number == 2
    assert revision.original_generated_payload is None


def test_login_issues_an_http_only_session_and_protects_content_routes(
    client: TestClient, session: Session
) -> None:
    user = User(email="admin@example.com", password_hash=hash_password("secure-password"))
    session.add(user)
    session.commit()

    denied = client.get("/api/v1/contents")
    logged_in = client.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": "secure-password"}
    )
    me = client.get("/api/v1/auth/me")
    contents = client.get("/api/v1/contents")

    assert denied.status_code == 401
    assert logged_in.status_code == 200
    assert "httponly" in logged_in.headers["set-cookie"].lower()
    assert me.json()["id"] == str(user.id)
    assert contents.status_code == 200
