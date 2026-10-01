"""Small, explainable diversity-aware ranker for factual insight candidates."""

from __future__ import annotations

from collections.abc import Iterable

from app.analytics.config import MAX_SELECTED_INSIGHTS, MINIMUM_SCRIPT_CONFIDENCE
from app.domain.models import InsightCandidate


class InsightRanker:
    def select(
        self, candidates: Iterable[InsightCandidate], maximum: int = MAX_SELECTED_INSIGHTS
    ) -> list[InsightCandidate]:
        selected: list[InsightCandidate] = []
        used_metrics: set[str] = set()
        used_types: set[str] = set()
        ordered = sorted(candidates, key=lambda item: (item.final_score, item.id.hex), reverse=True)
        for candidate in ordered:
            if not candidate.eligible or candidate.confidence_score < MINIMUM_SCRIPT_CONFIDENCE:
                continue
            metric_codes = {str(code) for code in candidate.metric_codes}
            if candidate.insight_type in used_types:
                continue
            if metric_codes and metric_codes.issubset(used_metrics):
                continue
            selected.append(candidate)
            used_types.add(candidate.insight_type)
            used_metrics.update(metric_codes)
            if len(selected) == maximum:
                break
        return selected
