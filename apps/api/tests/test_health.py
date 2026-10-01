from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_api_liveness() -> None:
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}


def test_provider_health_reports_readiness_without_calling_providers() -> None:
    response = TestClient(app).get("/api/v1/health/providers")

    assert response.status_code == 200
    assert response.json()["football"]["provider"] == "sportmonks"
    assert isinstance(response.json()["football"]["configured"], bool)
    assert isinstance(response.json()["llm"]["configured"], bool)


def test_request_payload_limit_rejects_oversized_declared_bodies() -> None:
    response = TestClient(app).post(
        "/api/v1/health", headers={"Content-Length": "1000001"}
    )

    assert response.status_code == 413


def test_api_allows_the_configured_web_origin() -> None:
    response = TestClient(app).options(
        "/api/v1/teams",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
