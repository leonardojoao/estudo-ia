"""Testes do endpoint básico de saúde."""

import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_PATH", ":memory:")

from fastapi.testclient import TestClient

from main import app


def test_health_returns_ok() -> None:
    """A API deve responder ao health check sem dependências externas."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
