"""Testes da integração com Ollama."""

import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("DATABASE_PATH", ":memory:")

from main import app  # noqa: E402
from app.services.text_generation.ollama_generator import OllamaGenerator  # noqa: E402
from app.services.text_generation.schemas import TextGenInput  # noqa: E402


def test_voices_endpoint_returns_english_voices() -> None:
    """A API deve disponibilizar vozes estáticas em inglês."""
    with TestClient(app) as client:
        response = client.get("/api/ollama/voices")

    assert response.status_code == 200
    assert response.json()[0]["name"].startswith("en-")


def test_models_endpoint_returns_empty_list_when_ollama_is_offline() -> None:
    """O diagnóstico não deve falhar com HTTP 500 quando Ollama está offline."""
    with patch.object(OllamaGenerator, "list_models", new=AsyncMock(return_value=[])):
        with TestClient(app) as client:
            response = client.get("/api/ollama/models")

    assert response.status_code == 200
    assert response.json() == []


def test_ollama_test_reports_available_models() -> None:
    """O endpoint de teste deve informar modelos disponíveis."""
    with patch.object(
        OllamaGenerator,
        "list_models",
        new=AsyncMock(return_value=["llama3"]),
    ):
        with TestClient(app) as client:
            response = client.post("/api/ollama/test")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "models": ["llama3"]}


@pytest.mark.asyncio
async def test_generate_normalizes_ollama_response() -> None:
    """O adaptador deve converter a resposta do cliente para o schema interno."""
    response = {"response": "texto gerado", "eval_count": 12}
    client = AsyncMock()
    client.generate.return_value = response
    with patch.object(OllamaGenerator, "_client", return_value=client):
        result = await OllamaGenerator("http://ollama").generate(
            TextGenInput(prompt="Escreva um roteiro", model="llama3"),
        )

    assert result.text == "texto gerado"
    assert result.tokens_used == 12


@pytest.mark.asyncio
async def test_generate_batch_calls_provider_sequentially() -> None:
    """A geração em lote deve executar a quantidade solicitada."""
    generator = OllamaGenerator("http://ollama")
    output = TextGenInput(prompt="Escreva", model="llama3")
    with patch.object(
        generator,
        "generate",
        new=AsyncMock(side_effect=lambda _: {"text": "ok"}),
    ) as generate:
        generate.side_effect = [
            type("Output", (), {"text": "um"})(),
            type("Output", (), {"text": "dois"})(),
            type("Output", (), {"text": "três"})(),
        ]
        result = await generator.generate_batch(output, 3)

    assert len(result) == 3
    assert generate.await_count == 3
