"""Deterministically turn configured duration policy into target word counts."""

from __future__ import annotations

from collections.abc import Sized
from math import floor

from app.domain.models import TeamProfile
from app.editorial.types import DurationContext

VALID_DURATIONS = {30, 45, 60, 90}


class DurationEngine:
    def choose(self, profile: TeamProfile, insights: Sized) -> DurationContext:
        seconds, mode = self._duration_seconds(profile, len(insights))
        # Editorial targets use conventional half-up rounding (45s at 150 wpm = 113 words),
        # rather than Python's banker's rounding.
        words = floor(seconds * profile.speech_rate_wpm / 60 + 0.5)
        tolerance = round(words * 0.08)
        return DurationContext(
            target_duration_seconds=seconds,
            target_word_count=words,
            minimum_word_count=words - tolerance,
            maximum_word_count=words + tolerance,
            mode=mode,
        )

    @staticmethod
    def _duration_seconds(profile: TeamProfile, insight_count: int) -> tuple[int, str]:
        if profile.forced_duration_seconds in VALID_DURATIONS:
            return profile.forced_duration_seconds, "FORCED"
        if profile.default_duration_mode in {"30", "45", "60", "90"}:
            return int(profile.default_duration_mode), "PROFILE"
        if insight_count <= 1:
            return 30, "AUTO"
        if insight_count == 2:
            return 45, "AUTO"
        return 60, "AUTO"
