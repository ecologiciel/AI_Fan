"""Build a character context solely from the selected team profile."""

from __future__ import annotations

from app.domain.models import TeamProfile
from app.editorial.types import CharacterContext


class CharacterEngine:
    def build(self, profile: TeamProfile, rivalry_intensity: int = 0) -> CharacterContext:
        provocation = min(
            100,
            profile.provocation_level + profile.rivalry_boost + rivalry_intensity // 4,
        )
        rules = [
            "Facts and figures must only come from supplied evidence.",
            "Emotional reactions may be subjective; factual claims remain exact.",
            "Avoid generic introductions and personal insults.",
        ]
        if profile.speech_style:
            rules.append(profile.speech_style)
        rules.extend(str(rule) for rule in profile.editorial_rules)
        rules.extend(f"Allowed expression: {expression}" for expression in profile.allowed_slang)
        rules.extend(f"Forbidden phrase: {phrase}" for phrase in profile.forbidden_phrases)
        return CharacterContext(
            language=profile.primary_script_language,
            locale=profile.locale,
            identity=profile.character_description or profile.fan_identity,
            tone={
                "emotion": profile.emotion_base_level,
                "humor": profile.humor_level,
                "provocation": provocation,
                "technical_depth": profile.technical_depth,
            },
            speech_rules=rules,
            cultural_context=profile.cultural_context,
        )
