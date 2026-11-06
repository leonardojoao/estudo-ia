"""Testes dos endpoints de configurações."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_PATH", ":memory:")

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

ADMIN_KEY = os.environ["SECRET_KEY"]


def test_get_settings_returns_defaults() -> None:
    """A API deve disponibilizar os defaults sem expor segredos."""
    with TestClient(app) as client:
        response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["ollama_url"] == "http://localhost:11434"
    assert "secret_key" not in data


def test_put_settings_updates_only_received_keys() -> None:
    """Atualização parcial deve preservar as demais configurações."""
    with TestClient(app) as client:
        response = client.put(
            "/api/settings",
            json={"ollama_model": "qwen2"},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert response.status_code == 200
    assert response.json()["data"]["ollama_model"] == "qwen2"
    assert response.json()["data"]["tts_voice"] == "en-US-JennyNeural"


def test_put_settings_rejects_invalid_url() -> None:
    """URL inválida deve retornar erro de validação sem persistir."""
    with TestClient(app) as client:
        response = client.put(
            "/api/settings",
            json={"ollama_url": "nao-e-url"},
            headers={"X-Admin-Key": ADMIN_KEY},
        )

    assert response.status_code == 422
