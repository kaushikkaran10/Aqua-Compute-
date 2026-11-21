import pytest
from fastapi.testclient import TestClient

import db
import llm
from main import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """Set up an isolated temporary SQLite database for each test."""
    db_file = tmp_path / "test_aquacompute.db"
    monkeypatch.setenv("DB_PATH", str(db_file))
    db.init_db()
    yield


@pytest.fixture
def mock_llm_ask(monkeypatch):
    """Mock the llm.ask function to avoid external API calls."""
    def _fake_ask(prompt: str, model_id: str) -> dict:
        return {
            "text": f"Generated answer for: {prompt}",
            "input_tokens": 60,
            "output_tokens": 120,
        }
    monkeypatch.setattr(llm, "ask", _fake_ask)
    return _fake_ask


client = TestClient(app)


def test_health_endpoint():
    """Verify that /health returns status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_response_shape_and_tier(mock_llm_ask):
    """Verify that /chat returns the exact required schema and valid tier."""
    response = client.post("/chat", json={"prompt": "What is Python?"})
    assert response.status_code == 200

    data = response.json()
    assert set(data.keys()) == {"reply", "routing", "usage", "footprint"}
    assert set(data["routing"].keys()) == {"tier", "model_name", "model_id", "reason", "estimated_tokens"}
    assert set(data["usage"].keys()) == {"input_tokens", "output_tokens"}
    assert set(data["footprint"].keys()) == {"energy_kwh", "direct_water_l", "indirect_water_l", "water_l", "carbon_g", "basis"}

    assert data["routing"]["tier"] in {"small", "medium", "large"}
    assert data["usage"]["input_tokens"] == 60
    assert data["usage"]["output_tokens"] == 120
    assert data["footprint"]["basis"] == "placeholder"


def test_chat_different_tiers_for_easy_and_hard(mock_llm_ask):
    """Verify that easy and hard prompts are assigned to different tiers."""
    easy_resp = client.post("/chat", json={"prompt": "Hello!"})
    hard_resp = client.post(
        "/chat",
        json={"prompt": "Prove step by step that x^2 = 2 has no rational solution."},
    )

    assert easy_resp.status_code == 200
    assert hard_resp.status_code == 200

    easy_tier = easy_resp.json()["routing"]["tier"]
    hard_tier = hard_resp.json()["routing"]["tier"]

    assert easy_tier == "small"
    assert hard_tier == "large"
    assert easy_tier != hard_tier


def test_chat_saves_run_and_history_totals(mock_llm_ask):
    """Verify that /chat persists runs and /history reflects them and computes correct totals."""
    client.post("/chat", json={"prompt": "Explain gravity simply."})
    client.post("/chat", json={"prompt": "Can you compare and optimize this process?"})

    history_resp = client.get("/history")
    assert history_resp.status_code == 200

    data = history_resp.json()
    assert len(data["runs"]) == 2
    assert data["totals"]["requests"] == 2
    assert data["totals"]["energy_kwh"] > 0
    assert data["totals"]["water_l"] > 0
    assert data["totals"]["carbon_g"] > 0
    assert data["totals"]["baseline_water_l"] > 0
    assert isinstance(data["totals"]["saved_percent"], int)


@pytest.mark.parametrize("empty_payload", [{"prompt": ""}, {"prompt": "   "}, {}])
def test_chat_empty_prompt_returns_422(empty_payload):
    """Verify that empty or whitespace prompts return HTTP 422."""
    response = client.post("/chat", json=empty_payload)
    assert response.status_code == 422


def test_chat_llm_failure_returns_502_and_saves_nothing(monkeypatch):
    """Verify that an LLM failure returns HTTP 502 and nothing is persisted to the database."""
    def _failing_ask(prompt: str, model_id: str):
        raise RuntimeError("Groq API timeout")

    monkeypatch.setattr(llm, "ask", _failing_ask)

    response = client.post("/chat", json={"prompt": "This should fail gracefully."})
    assert response.status_code == 502
    assert "LLM call failed" in response.json()["detail"]

    history_resp = client.get("/history")
    assert history_resp.status_code == 200
    history_data = history_resp.json()
    assert len(history_data["runs"]) == 0
    assert history_data["totals"]["requests"] == 0


def test_frontend_index_served():
    """Verify that index.html is served statically at the root route."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AquaCompute" in response.text
