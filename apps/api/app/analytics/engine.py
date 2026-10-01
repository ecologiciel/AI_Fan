"""Deterministic insight generation from normalized database statistics only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from math import fabs
from statistics import fmean, median, pstdev
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.analytics.config import MINIMUM_SCRIPT_CONFIDENCE, SCORE_WEIGHTS
from app.domain.models import (
    Baseline,
    Fixture,
    InsightCandidate,
    MetricDefinition,
    PlayerMatchStat,
    TeamFixtureLink,
    TeamMatchStat,
    TeamProfile,
    TeamRivalry,
)
from app.services.metric_registry import MetricRegistryService
from app.services.statistics import BaselineService


@dataclass(frozen=True)
class SelectedBaseline:
    record: Baseline
    quality_score: float


@dataclass(frozen=True)
class MetricEvaluation:
    definition: MetricDefinition
    stat: TeamMatchStat | None
    selected_baseline: SelectedBaseline | None
    candidate: InsightCandidate


class AnalyticsEngine:
    """Produces auditable candidates without a football-provider or LLM dependency."""

    def __init__(self) -> None:
        self._registry = MetricRegistryService()
        self._baseline_service = BaselineService()

    def recalculate(
        self,
        session: Session,
        fixture_id: UUID,
        team_profile_id: UUID,
        content_type: str,
    ) -> list[InsightCandidate]:
        fixture, profile, link = self._context(session, fixture_id, team_profile_id)
        self._registry.ensure_defaults(session)
        baseline_records = self._baseline_service.calculate_for_fixture(
            session, fixture_id, team_profile_id
        )
        baselines_by_metric: dict[str, list[Baseline]] = {}
        for baseline in baseline_records:
            baselines_by_metric.setdefault(baseline.metric_code, []).append(baseline)

        stats = {
            stat.metric_code: stat
            for stat in session.scalars(
                select(TeamMatchStat).where(
                    TeamMatchStat.fixture_id == fixture_id,
                    TeamMatchStat.team_external_id == profile.external_team_id,
                    TeamMatchStat.period == "ALL",
                )
            )
        }
        rivalry_intensity = self._rivalry_intensity(session, profile, fixture)
        evaluations: dict[str, MetricEvaluation] = {}
        candidates: list[InsightCandidate] = []
        for definition in self._registry.list_enabled(session, "team"):
            evaluation = self._evaluate_metric(
                session,
                fixture,
                link,
                profile,
                definition,
                stats.get(definition.code),
                baselines_by_metric.get(definition.code, []),
                content_type,
                rivalry_intensity,
            )
            evaluations[definition.code] = evaluation
            candidates.append(evaluation.candidate)

        candidates.extend(
            self._compound_candidates(
                session,
                fixture,
                profile,
                content_type,
                stats,
                evaluations,
                rivalry_intensity,
            )
        )
        candidates.extend(
            self._player_outlier_candidates(
                session, fixture, profile, content_type, rivalry_intensity
            )
        )
        session.commit()
        return self.list_candidates(session, fixture_id, team_profile_id, content_type)

    @staticmethod
    def list_candidates(
        session: Session, fixture_id: UUID, team_profile_id: UUID, content_type: str
    ) -> list[InsightCandidate]:
        return list(
            session.scalars(
                select(InsightCandidate)
                .where(
                    InsightCandidate.fixture_id == fixture_id,
                    InsightCandidate.team_profile_id == team_profile_id,
                    InsightCandidate.content_type == content_type,
                )
                .order_by(InsightCandidate.final_score.desc(), InsightCandidate.insight_type)
            )
        )

    def _evaluate_metric(
        self,
        session: Session,
        fixture: Fixture,
        link: TeamFixtureLink,
        profile: TeamProfile,
        definition: MetricDefinition,
        stat: TeamMatchStat | None,
        baseline_records: list[Baseline],
        content_type: str,
        rivalry_intensity: int,
    ) -> MetricEvaluation:
        key = f"metric:{definition.code}"
        if stat is None:
            candidate = self._upsert_candidate(
                session,
                fixture,
                profile,
                content_type,
                key,
                "METRIC_DEVIATION",
                f"Missing metric: {definition.code}",
                f"{definition.code} is unavailable for this fixture; it is excluded from analysis.",
                [],
                {},
                [definition.code],
                eligible=False,
                rejection_reason="MISSING_METRIC",
            )
            return MetricEvaluation(definition, None, None, candidate)

        selected = self._select_baseline(baseline_records, definition, link.team_side)
        if selected is None:
            candidate = self._upsert_candidate(
                session,
                fixture,
                profile,
                content_type,
                key,
                "METRIC_DEVIATION",
                f"Insufficient history: {definition.code}",
                (
                    f"{definition.code} has no baseline with at least "
                    f"{definition.min_sample_size} matches."
                ),
                [self._stat_evidence(fixture, stat)],
                {},
                [definition.code],
                eligible=False,
                rejection_reason="INSUFFICIENT_SAMPLE",
            )
            return MetricEvaluation(definition, stat, None, candidate)

        baseline_value = selected.record.mean_value
        if baseline_value is None:
            raise ValueError("Selected baseline cannot have an empty mean")
        absolute_difference = stat.metric_value - baseline_value
        relative_deviation = fabs(absolute_difference) / max(
            fabs(baseline_value), definition.metric_floor
        )
        deviation_score = min(relative_deviation / definition.default_anomaly_threshold, 1.0)
        confidence_score = self._confidence(stat, selected.record, definition)
        context_score = self._context_score(rivalry_intensity)
        novelty_score = self._novelty_score(
            session, fixture, profile, "METRIC_DEVIATION", deviation_score
        )
        final_score = self._final_score(
            deviation_score,
            definition.importance_weight,
            confidence_score,
            context_score,
            novelty_score,
        )
        direction = (
            "ABOVE"
            if absolute_difference > 0
            else "BELOW"
            if absolute_difference < 0
            else "NEUTRAL"
        )
        eligible = (
            relative_deviation >= definition.default_anomaly_threshold
            and confidence_score >= MINIMUM_SCRIPT_CONFIDENCE
        )
        rejection_reason = None if eligible else "NOT_ANOMALOUS"
        baseline = self._baseline_snapshot(selected)
        claim = (
            f"{definition.code} is {relative_deviation * 100:.1f}% {direction.lower()} "
            f"the {selected.record.window_type} baseline "
            f"({stat.metric_value:.2f} vs {baseline_value:.2f})."
        )
        candidate = self._upsert_candidate(
            session,
            fixture,
            profile,
            content_type,
            key,
            "METRIC_DEVIATION",
            f"{definition.code}: {direction} {selected.record.window_type}",
            claim,
            [self._stat_evidence(fixture, stat)],
            baseline,
            [definition.code],
            deviation_score,
            definition.importance_weight,
            confidence_score,
            context_score,
            novelty_score,
            final_score,
            direction,
            eligible,
            rejection_reason,
        )
        return MetricEvaluation(definition, stat, selected, candidate)

    def _compound_candidates(
        self,
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        content_type: str,
        stats: dict[str, TeamMatchStat],
        evaluations: dict[str, MetricEvaluation],
        rivalry_intensity: int,
    ) -> list[InsightCandidate]:
        candidates: list[InsightCandidate] = []
        scoreline = self._scoreline_truth_candidate(
            session, fixture, profile, content_type, stats, rivalry_intensity
        )
        if scoreline is not None:
            candidates.append(scoreline)
        possession = evaluations.get("possession_pct")
        threat = evaluations.get("xg") or evaluations.get("shots")
        if possession and threat and possession.candidate.eligible and threat.candidate.eligible:
            if possession.candidate.direction == "ABOVE" and threat.candidate.direction == "BELOW":
                candidates.append(
                    self._compound_from_metrics(
                        session,
                        fixture,
                        profile,
                        content_type,
                        "POSSESSION_WITHOUT_THREAT",
                        "Possession without threat",
                        "Possession rose au-dessus de la référence alors que la menace a baissé.",
                        possession,
                        threat,
                        rivalry_intensity,
                    )
                )
            elif (
                possession.candidate.direction == "BELOW" and threat.candidate.direction == "ABOVE"
            ):
                candidates.append(
                    self._compound_from_metrics(
                        session,
                        fixture,
                        profile,
                        content_type,
                        "LOW_POSSESSION_HIGH_THREAT",
                        "Low possession, high threat",
                        "La possession a baissé sous la référence alors que la menace a augmenté.",
                        possession,
                        threat,
                        rivalry_intensity,
                    )
                )
        return candidates

    def _player_outlier_candidates(
        self,
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        content_type: str,
        rivalry_intensity: int,
    ) -> list[InsightCandidate]:
        definitions = {
            definition.code.removeprefix("player_"): definition
            for definition in self._registry.list_enabled(session, "player")
        }
        current_stats = session.scalars(
            select(PlayerMatchStat).where(
                PlayerMatchStat.fixture_id == fixture.id,
                PlayerMatchStat.team_external_id == profile.external_team_id,
                PlayerMatchStat.period == "ALL",
            )
        )
        candidates: list[InsightCandidate] = []
        for stat in current_stats:
            definition = definitions.get(stat.metric_code)
            if definition is None or stat.metric_code == "minutes_played":
                continue
            candidates.append(
                self._evaluate_player_metric(
                    session, fixture, profile, content_type, stat, definition, rivalry_intensity
                )
            )
        return candidates

    def _evaluate_player_metric(
        self,
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        content_type: str,
        stat: PlayerMatchStat,
        definition: MetricDefinition,
        rivalry_intensity: int,
    ) -> InsightCandidate:
        key = f"player:{stat.player_external_id}:{stat.metric_code}"
        if stat.minutes_played is None or stat.minutes_played < 20:
            return self._upsert_candidate(
                session,
                fixture,
                profile,
                content_type,
                key,
                "PLAYER_OUTLIER",
                f"Insufficient player minutes: {stat.player_name}",
                (
                    f"{stat.player_name} played fewer than 20 minutes; "
                    "a per-90 comparison is excluded."
                ),
                [self._player_evidence(fixture, stat, None)],
                {},
                [definition.code],
                eligible=False,
                rejection_reason="INSUFFICIENT_MINUTES",
            )

        history = self._player_history(session, fixture, stat)
        last_five = history[:5]
        season = [item for item in history if item[0].season_id == fixture.season_id]
        last_five_record = self._upsert_player_baseline(
            session, fixture, stat, "LAST_5_PER_90", last_five
        )
        self._upsert_player_baseline(session, fixture, stat, "SEASON_PER_90", season)
        if (
            last_five_record.sample_size < definition.min_sample_size
            or last_five_record.mean_value is None
        ):
            return self._upsert_candidate(
                session,
                fixture,
                profile,
                content_type,
                key,
                "PLAYER_OUTLIER",
                f"Insufficient player history: {stat.player_name}",
                (
                    f"{stat.player_name} has fewer than {definition.min_sample_size} "
                    f"previous per-90 appearances for {stat.metric_code}."
                ),
                [self._player_evidence(fixture, stat, None)],
                {},
                [definition.code],
                eligible=False,
                rejection_reason="INSUFFICIENT_SAMPLE",
            )

        current_per_90 = stat.metric_value / stat.minutes_played * 90
        baseline_value = last_five_record.mean_value
        relative_deviation = fabs(current_per_90 - baseline_value) / max(
            fabs(baseline_value), definition.metric_floor
        )
        deviation_score = min(relative_deviation / definition.default_anomaly_threshold, 1.0)
        confidence = min(
            1.0,
            0.50 * stat.confidence
            + 0.30 * min(last_five_record.sample_size / 5, 1.0)
            + 0.20 * min(stat.minutes_played / 90, 1.0),
        )
        context = self._context_score(rivalry_intensity)
        novelty = self._novelty_score(session, fixture, profile, "PLAYER_OUTLIER", deviation_score)
        final_score = self._final_score(
            deviation_score, definition.importance_weight, confidence, context, novelty
        )
        direction = "ABOVE" if current_per_90 > baseline_value else "BELOW"
        eligible = (
            relative_deviation >= definition.default_anomaly_threshold
            and confidence >= MINIMUM_SCRIPT_CONFIDENCE
        )
        baseline = self._player_baseline_snapshot(last_five_record)
        claim = (
            f"{stat.player_name} recorded {current_per_90:.2f} {stat.metric_code} per 90, "
            f"versus {baseline_value:.2f} over the previous five appearances."
        )
        return self._upsert_candidate(
            session,
            fixture,
            profile,
            content_type,
            key,
            "PLAYER_OUTLIER",
            f"Player outlier: {stat.player_name} {stat.metric_code}",
            claim,
            [self._player_evidence(fixture, stat, current_per_90)],
            baseline,
            [definition.code],
            deviation_score,
            definition.importance_weight,
            confidence,
            context,
            novelty,
            final_score,
            direction,
            eligible,
            None if eligible else "NOT_ANOMALOUS",
        )

    @staticmethod
    def _player_history(
        session: Session, target: Fixture, stat: PlayerMatchStat
    ) -> list[tuple[Fixture, PlayerMatchStat]]:
        statement = (
            select(Fixture, PlayerMatchStat)
            .join(PlayerMatchStat, PlayerMatchStat.fixture_id == Fixture.id)
            .where(
                PlayerMatchStat.player_external_id == stat.player_external_id,
                PlayerMatchStat.metric_code == stat.metric_code,
                PlayerMatchStat.period == "ALL",
                PlayerMatchStat.minutes_played.is_not(None),
                PlayerMatchStat.minutes_played >= 20,
                Fixture.status == "FINISHED",
                Fixture.id != target.id,
                Fixture.kickoff_at < target.kickoff_at,
            )
            .order_by(Fixture.kickoff_at.desc())
        )
        return [(row[0], row[1]) for row in session.execute(statement)]

    @staticmethod
    def _upsert_player_baseline(
        session: Session,
        fixture: Fixture,
        stat: PlayerMatchStat,
        window_type: str,
        history: list[tuple[Fixture, PlayerMatchStat]],
    ) -> Baseline:
        values = [
            item.metric_value / item.minutes_played * 90
            for _, item in history
            if item.minutes_played
        ]
        context_key = f"fixture:{fixture.id}:player:{stat.player_external_id}:{stat.metric_code}"
        statement = select(Baseline).where(
            Baseline.entity_type == "player",
            Baseline.entity_external_id == stat.player_external_id,
            Baseline.competition_id == fixture.competition_id,
            Baseline.metric_code == f"player_{stat.metric_code}",
            Baseline.window_type == window_type,
            Baseline.context_key == context_key,
        )
        if fixture.competition_id is None:
            statement = statement.where(Baseline.competition_id.is_(None))
        record = session.scalar(statement)
        aggregates: dict[str, float | int | None] = {
            "sample_size": len(values),
            "mean_value": fmean(values) if values else None,
            "median_value": median(values) if values else None,
            "stddev_value": pstdev(values) if len(values) > 1 else None,
            "min_value": min(values) if values else None,
            "max_value": max(values) if values else None,
        }
        saved = {
            "window_size": 5 if window_type == "LAST_5_PER_90" else 0,
            "context": {
                "fixture_id": str(fixture.id),
                "player_name": stat.player_name,
                "metric_code": stat.metric_code,
                "normalization": "per_90",
            },
            **aggregates,
            "calculated_at": datetime.now(UTC),
        }
        if record is None:
            record = Baseline(
                entity_type="player",
                entity_external_id=stat.player_external_id,
                competition_id=fixture.competition_id,
                metric_code=f"player_{stat.metric_code}",
                window_type=window_type,
                context_key=context_key,
                **saved,
            )
            session.add(record)
        else:
            for field_name, value in saved.items():
                setattr(record, field_name, value)
        return record

    def _scoreline_truth_candidate(
        self,
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        content_type: str,
        stats: dict[str, TeamMatchStat],
        rivalry_intensity: int,
    ) -> InsightCandidate | None:
        if content_type != "POST_MATCH" or fixture.home_score is None or fixture.away_score is None:
            return None
        own_score, opponent_score = self._scores_for_profile(fixture, profile.external_team_id)
        if own_score is None or opponent_score is None:
            return None
        own_xg = stats.get("xg")
        opponent_external_id = self._opponent_external_id(fixture, profile.external_team_id)
        opponent_xg = session.scalar(
            select(TeamMatchStat).where(
                TeamMatchStat.fixture_id == fixture.id,
                TeamMatchStat.team_external_id == opponent_external_id,
                TeamMatchStat.metric_code == "xg",
                TeamMatchStat.period == "ALL",
            )
        )
        if own_xg is None or opponent_xg is None:
            return None
        xg_gap = own_xg.metric_value - opponent_xg.metric_value
        score_gap = own_score - opponent_score
        if score_gap > 0 and xg_gap < -0.4:
            insight_type, headline = "FLATTERING_WIN", "Scoreline vs xG: winning below xG"
        elif score_gap < 0 and xg_gap > 0.4:
            insight_type, headline = "UNLUCKY_DEFEAT", "Scoreline vs xG: losing above xG"
        elif score_gap > 0 and xg_gap > 0.4:
            insight_type, headline = "DOMINANT_WIN", "Scoreline and xG aligned"
        else:
            return None
        confidence = min(own_xg.confidence, opponent_xg.confidence)
        context = self._context_score(rivalry_intensity)
        novelty = self._novelty_score(session, fixture, profile, "SCORELINE_TRUTH", 1.0)
        final_score = self._final_score(1.0, 0.95, confidence, context, novelty)
        claim = (
            f"The score was {own_score}-{opponent_score}; xG was "
            f"{own_xg.metric_value:.2f}-{opponent_xg.metric_value:.2f}."
        )
        return self._upsert_candidate(
            session,
            fixture,
            profile,
            content_type,
            "compound:scoreline_truth",
            insight_type,
            headline,
            claim,
            [self._stat_evidence(fixture, own_xg), self._stat_evidence(fixture, opponent_xg)],
            {"score": {"team": own_score, "opponent": opponent_score}},
            ["goals", "xg"],
            1.0,
            0.95,
            confidence,
            context,
            novelty,
            final_score,
            "DIVERGENT" if score_gap * xg_gap < 0 else "ALIGNED",
            confidence >= MINIMUM_SCRIPT_CONFIDENCE,
            None if confidence >= MINIMUM_SCRIPT_CONFIDENCE else "LOW_CONFIDENCE",
        )

    def _compound_from_metrics(
        self,
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        content_type: str,
        insight_type: str,
        headline: str,
        neutral_summary: str,
        first: MetricEvaluation,
        second: MetricEvaluation,
        rivalry_intensity: int,
    ) -> InsightCandidate:
        first_candidate = first.candidate
        second_candidate = second.candidate
        deviation = min(
            1.0, (first_candidate.deviation_score + second_candidate.deviation_score) / 2
        )
        confidence = min(first_candidate.confidence_score, second_candidate.confidence_score)
        context = self._context_score(rivalry_intensity)
        novelty = self._novelty_score(session, fixture, profile, insight_type, deviation)
        final_score = self._final_score(deviation, 0.80, confidence, context, novelty)
        claim = f"{neutral_summary} {first_candidate.claim} {second_candidate.claim}"
        return self._upsert_candidate(
            session,
            fixture,
            profile,
            content_type,
            f"compound:{insight_type.lower()}",
            insight_type,
            headline,
            claim,
            [*first_candidate.evidence, *second_candidate.evidence],
            {"first": first_candidate.baseline, "second": second_candidate.baseline},
            [*first_candidate.metric_codes, *second_candidate.metric_codes],
            deviation,
            0.80,
            confidence,
            context,
            novelty,
            final_score,
            "MIXED",
            confidence >= MINIMUM_SCRIPT_CONFIDENCE,
            None if confidence >= MINIMUM_SCRIPT_CONFIDENCE else "LOW_CONFIDENCE",
        )

    @staticmethod
    def _context(
        session: Session, fixture_id: UUID, team_profile_id: UUID
    ) -> tuple[Fixture, TeamProfile, TeamFixtureLink]:
        fixture = session.get(Fixture, fixture_id)
        profile = session.get(TeamProfile, team_profile_id)
        link = session.get(
            TeamFixtureLink, {"fixture_id": fixture_id, "team_profile_id": team_profile_id}
        )
        if fixture is None or profile is None or link is None or not profile.external_team_id:
            raise LookupError("Fixture is not linked to a configured team profile")
        return fixture, profile, link

    @staticmethod
    def _select_baseline(
        records: list[Baseline], definition: MetricDefinition, team_side: str
    ) -> SelectedBaseline | None:
        context_order = (
            ("HOME_LAST_5", "LAST_5", "LAST_10", "SEASON", "COMPETITION_LAST_5")
            if team_side == "home"
            else ("AWAY_LAST_5", "LAST_5", "LAST_10", "SEASON", "COMPETITION_LAST_5")
        )
        candidates: list[tuple[int, SelectedBaseline]] = []
        for record in records:
            if record.mean_value is None or record.sample_size < definition.min_sample_size:
                continue
            try:
                position = context_order.index(record.window_type)
            except ValueError:
                continue
            sample_score = min(record.sample_size / 5, 1.0)
            context_score = 1.0 - (position * 0.12)
            quality = max(0.0, 0.55 * sample_score + 0.35 * context_score + 0.10)
            candidates.append((position, SelectedBaseline(record, quality)))
        if not candidates:
            return None
        # The specification makes the contextual window a hard preference once
        # its sample is sufficient; quality only breaks ties within that window.
        best_position = min(position for position, _ in candidates)
        return max(
            (candidate for position, candidate in candidates if position == best_position),
            key=lambda item: item.quality_score,
        )

    @staticmethod
    def _confidence(stat: TeamMatchStat, baseline: Baseline, definition: MetricDefinition) -> float:
        source_score = 1.0 if stat.source else 0.0
        period_score = 1.0 if stat.period == "ALL" else 0.5
        sample_score = min(baseline.sample_size / max(definition.min_sample_size, 5), 1.0)
        return min(
            1.0,
            0.35 * stat.confidence
            + 0.25 * source_score
            + 0.20 * period_score
            + 0.20 * sample_score,
        )

    @staticmethod
    def _context_score(rivalry_intensity: int) -> float:
        return min(1.0, 0.50 + rivalry_intensity / 200)

    @staticmethod
    def _final_score(
        deviation: float, importance: float, confidence: float, context: float, novelty: float
    ) -> int:
        value = (
            SCORE_WEIGHTS.deviation * deviation
            + SCORE_WEIGHTS.importance * importance
            + SCORE_WEIGHTS.confidence * confidence
            + SCORE_WEIGHTS.context * context
            + SCORE_WEIGHTS.novelty * novelty
        )
        return round(min(1.0, max(0.0, value)) * 100)

    @staticmethod
    def _stat_evidence(fixture: Fixture, stat: TeamMatchStat) -> dict[str, object]:
        return {
            "fixture_id": str(fixture.id),
            "metric": stat.metric_code,
            "team_external_id": stat.team_external_id,
            "current_value": stat.metric_value,
            "unit": stat.metric_unit,
            "source_provider": stat.source,
            "confidence": stat.confidence,
        }

    @staticmethod
    def _player_evidence(
        fixture: Fixture, stat: PlayerMatchStat, current_per_90: float | None
    ) -> dict[str, object]:
        return {
            "fixture_id": str(fixture.id),
            "metric": f"player_{stat.metric_code}",
            "player_external_id": stat.player_external_id,
            "player_name": stat.player_name,
            "current_value": stat.metric_value,
            "minutes_played": stat.minutes_played,
            "current_per_90": current_per_90,
            "source_provider": stat.source,
            "confidence": stat.confidence,
        }

    @staticmethod
    def _baseline_snapshot(selected: SelectedBaseline) -> dict[str, object]:
        record = selected.record
        return {
            "window_type": record.window_type,
            "sample_size": record.sample_size,
            "mean_value": record.mean_value,
            "median_value": record.median_value,
            "stddev_value": record.stddev_value,
            "quality_score": selected.quality_score,
        }

    @staticmethod
    def _player_baseline_snapshot(record: Baseline) -> dict[str, object]:
        return {
            "window_type": record.window_type,
            "sample_size": record.sample_size,
            "mean_value": record.mean_value,
            "median_value": record.median_value,
            "stddev_value": record.stddev_value,
            "normalization": "per_90",
        }

    def _novelty_score(
        self,
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        insight_type: str,
        deviation: float,
    ) -> float:
        if deviation >= 0.95:
            return 1.0
        prior_count = session.scalar(
            select(func.count(InsightCandidate.id))
            .join(Fixture, InsightCandidate.fixture_id == Fixture.id)
            .where(
                InsightCandidate.team_profile_id == profile.id,
                InsightCandidate.insight_type == insight_type,
                InsightCandidate.eligible.is_(True),
                Fixture.kickoff_at < fixture.kickoff_at,
            )
        )
        return 0.65 if prior_count and prior_count >= 3 else 0.90

    @staticmethod
    def _rivalry_intensity(session: Session, profile: TeamProfile, fixture: Fixture) -> int:
        opponent_id = AnalyticsEngine._opponent_external_id(fixture, profile.external_team_id)
        rivalry = session.scalar(
            select(TeamRivalry).where(
                TeamRivalry.team_profile_id == profile.id,
                TeamRivalry.opponent_external_team_id == opponent_id,
            )
        )
        return rivalry.intensity if rivalry else 0

    @staticmethod
    def _opponent_external_id(fixture: Fixture, team_external_id: str | None) -> str:
        if team_external_id == fixture.home_external_team_id:
            return fixture.away_external_team_id
        return fixture.home_external_team_id

    @staticmethod
    def _scores_for_profile(
        fixture: Fixture, team_external_id: str | None
    ) -> tuple[int | None, int | None]:
        if team_external_id == fixture.home_external_team_id:
            return fixture.home_score, fixture.away_score
        if team_external_id == fixture.away_external_team_id:
            return fixture.away_score, fixture.home_score
        return None, None

    @staticmethod
    def _upsert_candidate(
        session: Session,
        fixture: Fixture,
        profile: TeamProfile,
        content_type: str,
        calculation_key: str,
        insight_type: str,
        headline: str,
        claim: str,
        evidence: list[object],
        baseline: dict[str, object],
        metric_codes: list[object],
        deviation_score: float = 0.0,
        importance_score: float = 0.0,
        confidence_score: float = 0.0,
        context_score: float = 0.0,
        novelty_score: float = 0.0,
        final_score: int = 0,
        direction: str = "NEUTRAL",
        eligible: bool = False,
        rejection_reason: str | None = None,
    ) -> InsightCandidate:
        record = session.scalar(
            select(InsightCandidate).where(
                InsightCandidate.fixture_id == fixture.id,
                InsightCandidate.team_profile_id == profile.id,
                InsightCandidate.content_type == content_type,
                InsightCandidate.calculation_key == calculation_key,
            )
        )
        values = {
            "insight_type": insight_type,
            "headline_internal": headline,
            "claim": claim,
            "evidence": evidence,
            "baseline": baseline,
            "metric_codes": metric_codes,
            "deviation_score": deviation_score,
            "importance_score": importance_score,
            "confidence_score": confidence_score,
            "context_score": context_score,
            "novelty_score": novelty_score,
            "final_score": final_score,
            "direction": direction,
            "eligible": eligible,
            "rejection_reason": rejection_reason,
            "updated_at": datetime.now(UTC),
        }
        if record is None:
            record = InsightCandidate(
                fixture_id=fixture.id,
                team_profile_id=profile.id,
                content_type=content_type,
                calculation_key=calculation_key,
                **values,
            )
            session.add(record)
        else:
            for name, value in values.items():
                setattr(record, name, value)
        return record
