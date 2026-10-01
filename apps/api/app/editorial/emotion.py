"""Rule-based emotion selection; it never creates or changes football facts."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.models import Fixture, InsightCandidate, TeamProfile
from app.editorial.types import EmotionContext


class EmotionEngine:
    def build(
        self,
        fixture: Fixture,
        profile: TeamProfile,
        insights: Iterable[InsightCandidate],
        rivalry_intensity: int,
        content_type: str,
    ) -> EmotionContext:
        selected = list(insights)
        average_confidence = (
            sum(item.confidence_score for item in selected) / len(selected) if selected else 0.0
        )
        if content_type == "PRE_MATCH" or fixture.home_score is None or fixture.away_score is None:
            primary, secondary, arc, modifier = (
                "anticipatory",
                "analytical",
                [
                    "anticipatory",
                    "curious",
                    "analytical",
                ],
                5,
            )
        else:
            outcome = self._outcome(fixture, profile.external_team_id)
            insight_types = {item.insight_type for item in selected}
            if outcome == "WIN" and "FLATTERING_WIN" in insight_types:
                primary, secondary, arc, modifier = (
                    "relieved",
                    "critical",
                    [
                        "relieved",
                        "suspicious",
                        "critical",
                    ],
                    12,
                )
            elif outcome == "LOSS" and "UNLUCKY_DEFEAT" in insight_types:
                primary, secondary, arc, modifier = (
                    "frustrated",
                    "defiant",
                    [
                        "frustrated",
                        "defiant",
                        "analytical",
                    ],
                    15,
                )
            elif outcome == "WIN":
                primary, secondary, arc, modifier = (
                    "euphoric",
                    "analytical",
                    [
                        "euphoric",
                        "analytical",
                        "confident",
                    ],
                    20,
                )
            elif outcome == "LOSS":
                primary, secondary, arc, modifier = (
                    "disappointed",
                    "critical",
                    [
                        "disappointed",
                        "critical",
                        "defiant",
                    ],
                    15,
                )
            else:
                primary, secondary, arc, modifier = (
                    "tense",
                    "analytical",
                    [
                        "tense",
                        "analytical",
                        "questioning",
                    ],
                    8,
                )
        intensity = min(100, max(0, profile.emotion_base_level + modifier + rivalry_intensity // 5))
        return EmotionContext(
            primary=primary,
            secondary=secondary,
            intensity=intensity,
            confidence=round(average_confidence * 100),
            rivalry=rivalry_intensity,
            arc=arc,
        )

    @staticmethod
    def _outcome(fixture: Fixture, team_external_id: str | None) -> str:
        if team_external_id == fixture.home_external_team_id:
            own_score, opponent_score = fixture.home_score, fixture.away_score
        elif team_external_id == fixture.away_external_team_id:
            own_score, opponent_score = fixture.away_score, fixture.home_score
        else:
            return "DRAW"
        if own_score is None or opponent_score is None or own_score == opponent_score:
            return "DRAW"
        return "WIN" if own_score > opponent_score else "LOSS"
