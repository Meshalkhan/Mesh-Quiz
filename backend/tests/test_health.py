from fastapi.testclient import TestClient


def test_health_reports_service_and_groq_provider(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "mesh-quiz-api"
    assert body["default_llm_provider"] == "groq"
    assert body["llm_providers"] == [{"name": "groq", "configured": False}]
