from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


def test_api_manager_settings_and_selection_validation(monkeypatch, tmp_path):
    monkeypatch.setenv("FUND_INSIGHT_AUTO_INDEX", "0")
    monkeypatch.setenv("FUND_INSIGHT_DATA_DIR", str(tmp_path))
    with TestClient(app) as client:
        assert client.get("/api/health").json()["managers"] == 5
        assert len(client.get("/api/managers").json()) == 5
        response = client.post(
            "/api/threads",
            json={"mode": "single", "manager_ids": ["liu-xu", "zhang-kun"]},
        )
        assert response.status_code == 422
        saved = client.put("/api/settings/deepseek-key", json={"api_key": "sk-local-test-secret"})
        assert saved.status_code == 200
        assert saved.json()["deepseek_key_masked"] != "sk-local-test-secret"
        assert b"sk-local-test-secret" not in (tmp_path / "fund_insight.sqlite3").read_bytes()
