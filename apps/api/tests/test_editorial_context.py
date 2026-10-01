from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.models import Fixture, TeamFixtureLink, TeamMatchStat, TeamProfile, TeamRivalry
from app.editorial.duration import DurationEngine
from app.editorial.narrative import NarrativeAngleEngine
from app.services.editorial_context import EditorialContextService


def _profile(session: Session, *, forced_duration: int | None = None) -> TeamProfile:
    profile = TeamProfile(
        slug="editorial-team",
        display_name="Editorial Team",
        short_name="Editorial",
        football_provider="fake",
        external_team_id="team-1",
        primary_script_language="es",
        locale="es-ES",
        cultural_context={"region": "Catalunya", "dialect": "natural Spanish"},
        fan_identity="native_catalan_supporter",
        character_description="Native Catalan supporter speaking natural Spanish.",
        speech_style="Direct and fan-first.",
        emotion_base_level=70,
        humor_level=55,
        provocation_level=55,
        technical_depth=80,
        rivalry_boost=10,
        speech_rate_wpm=150,
        forced_duration_seconds=forced_duration,
        editorial_rules=["Never make up figures."],
    )
    profile.rivalries.append(
        TeamRivalry(
            opponent_external_team_id="team-2",
            opponent_name="Opponent",
            intensity=100,
            rivalry_label="Test rivalry",
        )
    )
    session.add(profile)
    session.commit()
    return profile


def _fixture(
    session: Session,
    external_id: str,
    kickoff_at: datetime,
    *,
    status: str = "FINISHED",
    home_score: int | None = None,
    away_score: int | None = None,
) -> Fixture:
    fixture = Fixture(
        provider="fake",
        external_fixture_id=external_id,
        home_external_team_id="team-1",
        away_external_team_id="team-2",
        home_name="Team One",
        away_name="Team Two",
        kickoff_at=kickoff_at,
        status=status,
        home_score=home_score,
        away_score=away_score,
        season_id="season-1",
    )
    session.add(fixture)
    session.flush()
    return fixture


def _stat(session: Session, fixture: Fixture, team_id: str, value: float) -> None:
    session.add(
        TeamMatchStat(
            fixture_id=fixture.id,
            team_external_id=team_id,
            metric_code="xg",
            metric_value=value,
            metric_unit="goals",
            source="fake",
            confidence=1.0,
        )
    )


def _complete_fixture(session: Session) -> tuple[TeamProfile, Fixture]:
    profile = _profile(session)
    now = datetime.now(UTC)
    for index, days in enumerate((4, 3, 2)):
        historical = _fixture(session, f"history-{index}", now - timedelta(days=days))
        _stat(session, historical, "team-1", 1.5)
    target = _fixture(session, "target", now, home_score=2, away_score=1)
    session.add(TeamFixtureLink(fixture_id=target.id, team_profile_id=profile.id, team_side="home"))
    _stat(session, target, "team-1", 0.5)
    _stat(session, target, "team-2", 1.4)
    session.commit()
    return profile, target


def test_internal_package_uses_profile_language_rivalry_and_factual_insights(
    session: Session,
) -> None:
    profile, fixture = _complete_fixture(session)

    package = EditorialContextService().build(session, fixture.id, profile.id, "POST_MATCH")

    assert package.ready_for_script is True
    assert package.language == "es"
    assert package.character.locale == "es-ES"
    assert package.character.identity == "Native Catalan supporter speaking natural Spanish."
    assert package.character.tone["provocation"] == 90
    assert package.emotion.primary == "relieved"
    assert package.emotion.secondary == "critical"
    assert package.narrative_angle.code == "SCORE_DOES_NOT_TELL_STORY"
    assert package.duration.target_duration_seconds == 30
    assert package.duration.target_word_count == 75
    assert all(insight.evidence for insight in package.insights)


def test_duration_uses_forced_mode_and_keeps_eight_percent_word_tolerance(session: Session) -> None:
    profile = _profile(session, forced_duration=60)

    duration = DurationEngine().choose(profile, [object(), object()])

    assert duration.mode == "FORCED"
    assert duration.target_word_count == 150
    assert (duration.minimum_word_count, duration.maximum_word_count) == (138, 162)


def test_duration_auto_uses_half_up_rounding_for_two_insights(session: Session) -> None:
    profile = _profile(session)

    duration = DurationEngine().choose(profile, [object(), object()])

    assert duration.mode == "AUTO"
    assert duration.target_duration_seconds == 45
    assert duration.target_word_count == 113


def test_narrative_engine_uses_straight_analysis_without_selected_insights() -> None:
    angle = NarrativeAngleEngine().choose([], rivalry_intensity=100)

    assert angle.code == "STRAIGHT_ANALYSIS"


def test_editorial_context_endpoint_returns_a_script_ready_package(
    authenticated_client: TestClient, session: Session
) -> None:
    profile, fixture = _complete_fixture(session)

    response = authenticated_client.post(
        f"/api/v1/fixtures/{fixture.id}/editorial-context?team_id={profile.id}"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ready_for_script"] is True
    assert body["character"]["locale"] == "es-ES"
    assert body["duration"]["target_word_count"] == 75
