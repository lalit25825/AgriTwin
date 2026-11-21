from fastapi.testclient import TestClient

from agritwin_ai.web import app as app_module


client = TestClient(app_module.app)


def test_health_reports_provider_configuration(monkeypatch):
    monkeypatch.setattr(app_module, "GROQ_API_KEY", "")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["provider_configured"] is False
    assert body["active_agents"] == 4
    assert body["market_data"]["records"] == 18367
    assert body["market_data"]["snapshot_date"] == "2026-09-09"


def test_agents_endpoint_distinguishes_active_and_planned_modules():
    response = client.get("/api/agents")
    assert response.status_code == 200
    agents = {agent["id"]: agent for agent in response.json()["agents"]}
    assert agents["harvest"]["status"] == "active"
    assert agents["climate"]["status"] == "active"
    assert agents["market"]["status"] == "active"
    assert agents["logistics"]["status"] == "active"
    assert agents["disease"]["status"] == "planned"
    assert agents["storage"]["status"] == "planned"


def test_chat_requires_provider_key(monkeypatch):
    monkeypatch.setattr(app_module, "GROQ_API_KEY", "")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = client.post(
        "/api/chat",
        json={"message": "Hello AgriTwin", "session_id": "test-session-0001"},
    )
    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_chat_returns_serialized_runtime_result(monkeypatch):
    class FakeRuntime:
        def run(self, agent, message):
            assert agent == "coordinator"
            assert message == "Should I harvest onions?"
            return {"recommendation": "HARVEST", "price": 2400.0}, ["harvest", "climate"], {"run_harvest": "ready"}

    class FakeManager:
        def get(self, session_id):
            assert session_id == "test-session-0002"
            return FakeRuntime()

    monkeypatch.setattr(app_module, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(app_module, "session_manager", FakeManager())
    response = client.post(
        "/api/chat",
        json={
            "message": "Should I harvest onions?",
            "session_id": "test-session-0002",
            "agent": "coordinator",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["response"]["recommendation"] == "HARVEST"
    assert body["agents_used"] == ["harvest", "climate"]
    assert body["observations"]["run_harvest"] == "ready"


def test_chat_rejects_invalid_session_id():
    response = client.post(
        "/api/chat",
        json={"message": "hello", "session_id": "bad session id"},
    )
    assert response.status_code == 422
