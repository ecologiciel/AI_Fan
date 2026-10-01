"""Orchestrate the deterministic package provided to the future Script Engine."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.engine import AnalyticsEngine
from app.analytics.ranker import InsightRanker
from app.domain.models import Fixture, TeamFixtureLink, TeamProfile, TeamRivalry
from app.editorial.character import CharacterEngine
from app.editorial.duration import DurationEngine
from app.editorial.emotion import EmotionEngine
from app.editorial.narrative import NarrativeAngleEngine
from app.editorial.types import EditorialInsight, EditorialPackage


class EditorialContextService:
    def __init__(self) -> None:
        self._analytics = AnalyticsEngine()
        self._ranker = InsightRanker()
        self._character = CharacterEngine()
        self._emotion = EmotionEngine()
        self._narrative = NarrativeAngleEngine()
        self._duration = DurationEngine()

    def build(
        self,
        session: Session,
        fixture_id: UUID,
        team_profile_id: UUID,
        content_type: str,
        recalculate_insights: bool = True,
    ) -> EditorialPackage:
        fixture, profile = self._load_context(session, fixture_id, team_profile_id)
        candidates = (
            self._analytics.recalculate(session, fixture_id, team_profile_id, content_type)
            if recalculate_insights
            else self._analytics.list_candidates(session, fixture_id, team_profile_id, content_type)
        )
        selected = self._ranker.select(candidates)
        rivalry = self._rivalry_intensity(session, fixture, profile)
        character = self._character.build(profile, rivalry)
        emotion = self._emotion.build(fixture, profile, selected, rivalry, content_type)
        narrative_angle = self._narrative.choose(selected, rivalry)
        duration = self._duration.choose(profile, selected)
        editorial_insights = [
            EditorialInsight(
                id=candidate.id,
                insight_type=candidate.insight_type,
                claim=candidate.claim,
                evidence=candidate.evidence,
                final_score=candidate.final_score,
                confidence_score=candidate.confidence_score,
            )
            for candidate in selected
        ]
        ready = bool(editorial_insights)
        return EditorialPackage(
            fixture_id=fixture.id,
            team_profile_id=profile.id,
            content_type=content_type,
            language=profile.primary_script_language,
            match=self._match_context(fixture, profile),
            character=character,
            emotion=emotion,
            narrative_angle=narrative_angle,
            duration=duration,
            insights=editorial_insights,
            ready_for_script=ready,
            readiness_reason=None if ready else "NO_ELIGIBLE_INSIGHTS",
        )

    @staticmethod
    def _load_context(
        session: Session, fixture_id: UUID, team_profile_id: UUID
    ) -> tuple[Fixture, TeamProfile]:
        fixture = session.get(Fixture, fixture_id)
        profile = session.get(TeamProfile, team_profile_id)
        link = session.get(
            TeamFixtureLink, {"fixture_id": fixture_id, "team_profile_id": team_profile_id}
        )
        if fixture is None or profile is None or link is None or not profile.external_team_id:
            raise LookupError("Fixture is not linked to a configured team profile")
        return fixture, profile

    @staticmethod
    def _rivalry_intensity(session: Session, fixture: Fixture, profile: TeamProfile) -> int:
        opponent_external_id = (
            fixture.away_external_team_id
            if profile.external_team_id == fixture.home_external_team_id
            else fixture.home_external_team_id
        )
        rivalry = session.scalar(
            select(TeamRivalry).where(
                TeamRivalry.team_profile_id == profile.id,
                TeamRivalry.opponent_external_team_id == opponent_external_id,
            )
        )
        return rivalry.intensity if rivalry else 0

    @staticmethod
    def _match_context(fixture: Fixture, profile: TeamProfile) -> dict[str, object]:
        is_home = profile.external_team_id == fixture.home_external_team_id
        own_score = fixture.home_score if is_home else fixture.away_score
        opponent_score = fixture.away_score if is_home else fixture.home_score
        return {
            "team": profile.display_name,
            "opponent": fixture.away_name if is_home else fixture.home_name,
            "kickoff_at": fixture.kickoff_at.isoformat(),
            "status": fixture.status,
            "score": {"team": own_score, "opponent": opponent_score},
        }
