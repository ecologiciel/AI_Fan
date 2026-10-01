"""Select a narrative angle with transparent priority rules."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.models import InsightCandidate
from app.editorial.types import NarrativeAngle


class NarrativeAngleEngine:
    def choose(
        self, insights: Iterable[InsightCandidate], rivalry_intensity: int
    ) -> NarrativeAngle:
        selected = list(insights)
        types = {item.insight_type for item in selected}
        if types & {"FLATTERING_WIN", "UNLUCKY_DEFEAT"}:
            return NarrativeAngle("SCORE_DOES_NOT_TELL_STORY", "Scoreline Truth Check is selected.")
        if "PLAYER_OUTLIER" in types:
            return NarrativeAngle("PLAYER_SPOTLIGHT", "A player outlier is selected.")
        if types & {"POSSESSION_WITHOUT_THREAT", "LOW_POSSESSION_HIGH_THREAT"}:
            return NarrativeAngle(
                "TACTICAL_WARNING", "A possession-versus-threat pattern is selected."
            )
        if rivalry_intensity >= 80 and selected:
            return NarrativeAngle(
                "RIVALRY_PROVOCATION", "A high-intensity rivalry adds editorial context."
            )
        if any(item.direction == "BELOW" for item in selected):
            return NarrativeAngle("UNEXPECTED_NEGATIVE", "A selected metric is below its baseline.")
        if any(item.direction == "ABOVE" for item in selected):
            return NarrativeAngle("UNEXPECTED_POSITIVE", "A selected metric is above its baseline.")
        if selected:
            return NarrativeAngle(
                "HIDDEN_STAT", "A factual insight is available without a stronger rule."
            )
        return NarrativeAngle(
            "STRAIGHT_ANALYSIS", "No strong insight justifies a forced narrative twist."
        )
