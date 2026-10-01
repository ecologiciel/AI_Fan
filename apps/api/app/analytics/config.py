"""Central analytics policy; score weights do not live in individual rules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalyticsScoreWeights:
    deviation: float = 0.35
    importance: float = 0.25
    confidence: float = 0.15
    context: float = 0.15
    novelty: float = 0.10


SCORE_WEIGHTS = AnalyticsScoreWeights()
MINIMUM_SCRIPT_CONFIDENCE = 0.60
MINIMUM_PLAYER_MINUTES = 20.0
MAX_SELECTED_INSIGHTS = 3
