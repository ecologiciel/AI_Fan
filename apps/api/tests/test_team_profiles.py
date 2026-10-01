from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seed import seed_defaults
from app.domain.models import TeamProfile, TeamRivalry


def test_barcelona_seed_is_configuration_and_idempotent(session: Session) -> None:
    seed_defaults(session)
    seed_defaults(session)

    profile = session.scalar(select(TeamProfile).where(TeamProfile.slug == "barcelona"))
    assert profile is not None
    assert profile.primary_script_language == "es"
    assert profile.locale == "es-ES"
    assert profile.fan_identity == "native_catalan_barca_supporter"
    assert profile.external_team_id is None
    assert profile.editorial_rules
    assert len(profile.rivalries) == 1
    assert profile.rivalries[0].rivalry_label == "El Clásico"


def test_admin_can_create_and_update_another_team_without_code(
    authenticated_client: TestClient,
) -> None:
    payload = {
        "slug": "real-madrid",
        "display_name": "Real Madrid",
        "short_name": "Real Madrid",
        "football_provider": "sportmonks",
        "external_team_id": "configured-by-admin",
        "timezone": "Europe/Madrid",
        "primary_script_language": "es",
        "locale": "es-ES",
        "fan_identity": "native_madrid_supporter",
        "character_description": "Configurable Madrid supporter.",
    }
    create_response = authenticated_client.post("/api/v1/teams", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["slug"] == "real-madrid"
    assert created["profile_version"] == 1

    duplicate_response = authenticated_client.post("/api/v1/teams", json=payload)
    assert duplicate_response.status_code == 409

    update_response = authenticated_client.patch(
        f"/api/v1/teams/{created['id']}", json={"humor_level": 72, "locale": "es-ES"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["humor_level"] == 72
    assert update_response.json()["profile_version"] == 2


def test_rivalries_are_scoped_to_their_team_and_versioned(
    authenticated_client: TestClient, session: Session
) -> None:
    profile = TeamProfile(
        slug="test-team",
        display_name="Test Team",
        short_name="Test",
        primary_script_language="en",
        locale="en-GB",
        fan_identity="test_supporter",
    )
    session.add(profile)
    session.commit()

    response = authenticated_client.post(
        f"/api/v1/teams/{profile.id}/rivalries",
        json={
            "opponent_external_team_id": "opponent-1",
            "opponent_name": "Opponent FC",
            "intensity": 80,
            "rivalry_label": "Derby",
            "custom_character_rules": {"emotion_boost": 20},
        },
    )
    assert response.status_code == 201
    rivalry = response.json()
    assert (
        authenticated_client.get(f"/api/v1/teams/{profile.id}/rivalries").json()[0]["id"]
        == rivalry["id"]
    )
    assert session.get(TeamProfile, profile.id).profile_version == 2
    assert session.scalar(select(TeamRivalry)).intensity == 80
