from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.analytics.engine import AnalyticsEngine
from app.analytics.ranker import InsightRanker
from app.domain.models import (
    Baseline,
    Fixture,
    MetricDefinition,
    PlayerMatchStat,
    TeamFixtureLink,
    TeamMatchStat,
    TeamProfile,
)


def _profile(session: Session) -> TeamProfile:
    profile = TeamProfile(
        slug="analytics-team",
        display_name="Analytics Team",
        short_name="Analytics",
        football_provider="fake",
        external_team_id="team-1",
        primary_script_language="en",
        locale="en-GB",
        fan_identity="test_supporter",
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


def _team_stat(session: Session, fixture: Fixture, team_id: str, code: str, value: float) -> None:
    session.add(
        TeamMatchStat(
            fixture_id=fixture.id,
            team_external_id=team_id,
            metric_code=code,
            metric_value=value,
            metric_unit="percent" if code == "possession_pct" else "count",
            source="fake",
            confidence=1.0,
        )
    )


def test_engine_creates_traceable_metric_and_compound_insights(session: Session) -> None:
    profile = _profile(session)
    now = datetime.now(UTC)
    for index, days in enumerate((4, 3, 2)):
        historical = _fixture(session, f"historical-{index}", now - timedelta(days=days))
        _team_stat(session, historical, "team-1", "xg", 1.5)
        _team_stat(session, historical, "team-1", "possession_pct", 50)
    target = _fixture(session, "target", now, home_score=2, away_score=1)
    session.add(TeamFixtureLink(fixture_id=target.id, team_profile_id=profile.id, team_side="home"))
    _team_stat(session, target, "team-1", "xg", 0.6)
    _team_stat(session, target, "team-1", "possession_pct", 70)
    _team_stat(session, target, "team-2", "xg", 1.6)
    session.commit()

    candidates = AnalyticsEngine().recalculate(session, target.id, profile.id, "POST_MATCH")

    xg = next(item for item in candidates if item.calculation_key == "metric:xg")
    possession_without_threat = next(
        item for item in candidates if item.insight_type == "POSSESSION_WITHOUT_THREAT"
    )
    scoreline = next(item for item in candidates if item.insight_type == "FLATTERING_WIN")
    assert xg.eligible is True
    assert xg.baseline["window_type"] == "HOME_LAST_5"
    assert xg.evidence[0]["current_value"] == 0.6
    assert possession_without_threat.eligible is True
    assert scoreline.claim == "The score was 2-1; xG was 0.60-1.60."
    selected = InsightRanker().select(candidates)
    assert 2 <= len(selected) <= 3
    assert len({item.insight_type for item in selected}) == len(selected)


def test_missing_metric_is_persisted_as_an_ineligible_candidate(session: Session) -> None:
    profile = _profile(session)
    now = datetime.now(UTC)
    historical = _fixture(session, "historical", now - timedelta(days=1))
    _team_stat(session, historical, "team-1", "shots", 10)
    target = _fixture(session, "target", now, home_score=1, away_score=0)
    session.add(TeamFixtureLink(fixture_id=target.id, team_profile_id=profile.id, team_side="home"))
    _team_stat(session, target, "team-1", "shots", 15)
    session.commit()

    candidates = AnalyticsEngine().recalculate(session, target.id, profile.id, "POST_MATCH")

    missing_xg = next(item for item in candidates if item.calculation_key == "metric:xg")
    assert missing_xg.eligible is False
    assert missing_xg.rejection_reason == "MISSING_METRIC"
    assert missing_xg.evidence == []


def test_baseline_selection_prefers_sufficient_home_context_over_larger_generic_sample() -> None:
    definition = MetricDefinition(
        code="xg",
        display_name="Expected goals",
        scope="team",
        unit="goals",
        higher_is_better=True,
        importance_weight=0.9,
        editorial_weight=0.9,
        default_anomaly_threshold=0.2,
        metric_floor=0.1,
        min_sample_size=3,
        provider_mapping={},
    )
    home = Baseline(
        entity_type="team",
        entity_external_id="team-1",
        metric_code="xg",
        window_type="HOME_LAST_5",
        window_size=5,
        context_key="home",
        context={},
        sample_size=3,
        mean_value=1.2,
    )
    generic = Baseline(
        entity_type="team",
        entity_external_id="team-1",
        metric_code="xg",
        window_type="LAST_5",
        window_size=5,
        context_key="generic",
        context={},
        sample_size=5,
        mean_value=1.5,
    )

    selected = AnalyticsEngine._select_baseline([generic, home], definition, "home")

    assert selected is not None
    assert selected.record.window_type == "HOME_LAST_5"


def test_player_outlier_uses_per_90_and_rejects_short_appearances(session: Session) -> None:
    profile = _profile(session)
    now = datetime.now(UTC)
    for index, days in enumerate((4, 3, 2)):
        historical = _fixture(session, f"player-history-{index}", now - timedelta(days=days))
        session.add(
            PlayerMatchStat(
                fixture_id=historical.id,
                player_external_id="player-1",
                player_name="Player One",
                team_external_id="team-1",
                minutes_played=90,
                metric_code="key_passes",
                metric_value=1,
                metric_unit="count",
                source="fake",
            )
        )
    target = _fixture(session, "player-target", now, home_score=1, away_score=0)
    session.add(TeamFixtureLink(fixture_id=target.id, team_profile_id=profile.id, team_side="home"))
    session.add_all(
        [
            PlayerMatchStat(
                fixture_id=target.id,
                player_external_id="player-1",
                player_name="Player One",
                team_external_id="team-1",
                minutes_played=90,
                metric_code="key_passes",
                metric_value=5,
                metric_unit="count",
                source="fake",
            ),
            PlayerMatchStat(
                fixture_id=target.id,
                player_external_id="player-2",
                player_name="Player Two",
                team_external_id="team-1",
                minutes_played=15,
                metric_code="key_passes",
                metric_value=2,
                metric_unit="count",
                source="fake",
            ),
        ]
    )
    session.commit()

    candidates = AnalyticsEngine().recalculate(session, target.id, profile.id, "POST_MATCH")

    outlier = next(
        item for item in candidates if item.calculation_key == "player:player-1:key_passes"
    )
    short_appearance = next(
        item for item in candidates if item.calculation_key == "player:player-2:key_passes"
    )
    assert outlier.eligible is True
    assert outlier.baseline["normalization"] == "per_90"
    assert outlier.evidence[0]["current_per_90"] == 5
    assert short_appearance.rejection_reason == "INSUFFICIENT_MINUTES"


def test_analytics_endpoints_recalculate_and_return_selected_candidates(
    authenticated_client: TestClient, session: Session
) -> None:
    profile = _profile(session)
    now = datetime.now(UTC)
    for index, days in enumerate((4, 3, 2)):
        historical = _fixture(session, f"h-{index}", now - timedelta(days=days))
        _team_stat(session, historical, "team-1", "xg", 1.5)
    target = _fixture(session, "api-target", now, home_score=2, away_score=1)
    session.add(TeamFixtureLink(fixture_id=target.id, team_profile_id=profile.id, team_side="home"))
    _team_stat(session, target, "team-1", "xg", 0.5)
    _team_stat(session, target, "team-2", "xg", 1.4)
    session.commit()

    response = authenticated_client.post(
        f"/api/v1/fixtures/{target.id}/recalculate-insights?team_id={profile.id}"
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(item["insight_type"] == "FLATTERING_WIN" for item in payload)
    assert any(item["selected"] for item in payload)
