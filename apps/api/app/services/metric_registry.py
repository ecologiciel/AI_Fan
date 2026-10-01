"""Database-backed registry for metrics usable by the deterministic analytics engine."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import MetricDefinition


@dataclass(frozen=True)
class DefaultMetric:
    code: str
    display_name: str
    scope: str
    unit: str
    higher_is_better: bool | None
    importance_weight: float
    editorial_weight: float
    default_anomaly_threshold: float
    metric_floor: float
    min_sample_size: int = 3


DEFAULT_METRICS = (
    DefaultMetric("goals", "Goals", "team", "count", True, 0.90, 0.75, 0.30, 1.0),
    DefaultMetric("xg", "Expected goals", "team", "goals", True, 0.95, 0.95, 0.20, 0.10),
    DefaultMetric("shots", "Shots", "team", "count", True, 0.65, 0.70, 0.25, 1.0),
    DefaultMetric(
        "shots_on_target", "Shots on target", "team", "count", True, 0.75, 0.80, 0.25, 1.0
    ),
    DefaultMetric("possession_pct", "Possession", "team", "percent", None, 0.40, 0.50, 0.10, 1.0),
    DefaultMetric("passes", "Passes", "team", "count", True, 0.35, 0.35, 0.20, 1.0),
    DefaultMetric(
        "pass_accuracy_pct", "Pass accuracy", "team", "percent", True, 0.40, 0.45, 0.08, 1.0
    ),
    DefaultMetric("corners", "Corners", "team", "count", True, 0.45, 0.55, 0.30, 1.0),
    DefaultMetric("fouls", "Fouls", "team", "count", False, 0.30, 0.35, 0.35, 1.0),
    DefaultMetric("yellow_cards", "Yellow cards", "team", "count", False, 0.35, 0.45, 0.50, 1.0),
    DefaultMetric("red_cards", "Red cards", "team", "count", False, 0.85, 0.90, 0.50, 1.0),
    DefaultMetric(
        "player_xg", "Player expected goals", "player", "goals", True, 0.80, 0.85, 0.30, 0.10
    ),
    DefaultMetric("player_shots", "Player shots", "player", "count", True, 0.60, 0.65, 0.35, 1.0),
    DefaultMetric(
        "player_key_passes", "Player key passes", "player", "count", True, 0.65, 0.75, 0.35, 1.0
    ),
    DefaultMetric(
        "player_tackles", "Player tackles", "player", "count", True, 0.45, 0.45, 0.40, 1.0
    ),
    DefaultMetric(
        "player_interceptions",
        "Player interceptions",
        "player",
        "count",
        True,
        0.45,
        0.45,
        0.40,
        1.0,
    ),
)


class MetricRegistryService:
    def ensure_defaults(self, session: Session) -> int:
        existing_codes = set(session.scalars(select(MetricDefinition.code)))
        created = 0
        for metric in DEFAULT_METRICS:
            if metric.code in existing_codes:
                continue
            session.add(
                MetricDefinition(
                    code=metric.code,
                    display_name=metric.display_name,
                    scope=metric.scope,
                    unit=metric.unit,
                    higher_is_better=metric.higher_is_better,
                    importance_weight=metric.importance_weight,
                    editorial_weight=metric.editorial_weight,
                    default_anomaly_threshold=metric.default_anomaly_threshold,
                    metric_floor=metric.metric_floor,
                    min_sample_size=metric.min_sample_size,
                    provider_mapping={"sportmonks": metric.code.removeprefix("player_")},
                )
            )
            created += 1
        if created:
            session.commit()
        return created

    @staticmethod
    def list_enabled(session: Session, scope: str) -> list[MetricDefinition]:
        return list(
            session.scalars(
                select(MetricDefinition)
                .where(MetricDefinition.scope == scope, MetricDefinition.enabled.is_(True))
                .order_by(MetricDefinition.code)
            )
        )
