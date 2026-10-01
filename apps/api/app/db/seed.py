from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.domain.models import TeamProfile, TeamRivalry
from app.services.auth import AuthService
from app.services.metric_registry import MetricRegistryService


def seed_defaults(session: Session | None = None) -> None:
    """Insert the pilot profile once; it remains regular configurable database data."""
    settings = get_settings()
    owns_session = session is None
    database_session = session or SessionLocal()
    try:
        MetricRegistryService().ensure_defaults(database_session)
        AuthService().ensure_admin(database_session)
        existing = database_session.scalar(
            select(TeamProfile).where(TeamProfile.slug == "barcelona")
        )
        if existing is not None:
            return
        barcelona = TeamProfile(
            slug="barcelona",
            display_name="FC Barcelona",
            short_name="Barça",
            active=True,
            football_provider="sportmonks",
            external_team_id=settings.barcelona_external_team_id,
            country="Spain",
            city="Barcelona",
            timezone="Europe/Madrid",
            primary_script_language="es",
            locale="es-ES",
            cultural_context={
                "region": "Catalunya",
                "fan_identity": "native_catalan_barca_supporter",
                "script_language": "Spanish",
                "note": (
                    "Aficionado catalán nativo que se dirige en español a una audiencia de fútbol."
                ),
            },
            fan_identity="native_catalan_barca_supporter",
            character_name="Aficionado culé",
            character_description="Supporter catalan natif et passionné du FC Barcelona.",
            speech_style="Oral, direct, émotionnel et rigoureux sur les faits.",
            speech_rate_wpm=150,
            emotion_base_level=75,
            humor_level=55,
            provocation_level=55,
            technical_depth=80,
            optimism_bias=60,
            self_criticism_level=70,
            editorial_rules=[
                "Le personnage aime le Barça mais ne falsifie jamais une statistique.",
                "Il peut critiquer l'équipe quand les données le justifient.",
                "Il peut taquiner un rival mais pas insulter des personnes.",
                "L'émotion est subjective ; les affirmations statistiques restent factuelles.",
                "Pas de salutations longues en début de Short.",
                "Le hook commence immédiatement.",
            ],
        )
        barcelona.rivalries.append(
            TeamRivalry(
                opponent_external_team_id="real-madrid",
                opponent_name="Real Madrid",
                intensity=100,
                rivalry_label="El Clásico",
                custom_character_rules={"provocation_boost": 25, "emotion_boost": 20},
            )
        )
        database_session.add(barcelona)
        database_session.commit()
    finally:
        if owns_session:
            database_session.close()


if __name__ == "__main__":
    seed_defaults()
