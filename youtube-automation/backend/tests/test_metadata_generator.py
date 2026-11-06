"""Testes do gerador de metadata."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import OllamaUnavailableError
from app.services.metadata.generator import generate_description, generate_title


@pytest.mark.asyncio
async def test_generate_title_uses_default_prompt_and_limit():
    """Título usa o texto narrado e respeita 100 caracteres."""
    result = type("Result", (), {"text": "x" * 150})()
    generator = AsyncMock(return_value=result)

    with patch(
        "app.services.metadata.generator.OllamaGenerator.generate",
        new=generator,
    ):
        title = await generate_title("Narrated text", "http://ollama", "llama3")

    assert len(title) == 100
    prompt = generator.await_args.args[0].prompt
    assert "Narrated text" in prompt
    assert "max 100 chars" in prompt


@pytest.mark.asyncio
async def test_generate_description_uses_custom_template_and_limit():
    """Descrição substitui template customizado e respeita 5000 caracteres."""
    result = type("Result", (), {"text": " description " + "x" * 6000})()
    generator = AsyncMock(return_value=result)

    with patch(
        "app.services.metadata.generator.OllamaGenerator.generate",
        new=generator,
    ):
        description = await generate_description(
            "Narrated text",
            "http://ollama",
            "llama3",
            description_prompt="Explain this: {text}",
        )

    assert len(description) == 5000
    assert description.startswith("description")
    assert generator.await_args.args[0].prompt == "Explain this: Narrated text"


@pytest.mark.asyncio
async def test_custom_prompt_without_placeholder_keeps_narrated_context():
    """Template sem placeholder ainda recebe o texto narrado."""
    result = type("Result", (), {"text": "Title"})()
    generator = AsyncMock(return_value=result)

    with patch(
        "app.services.metadata.generator.OllamaGenerator.generate",
        new=generator,
    ):
        await generate_title(
            "Narrated text",
            "http://ollama",
            "llama3",
            title_prompt="Create a concise title",
        )

    assert "Narrated text" in generator.await_args.args[0].prompt


@pytest.mark.asyncio
async def test_empty_narrator_text_is_rejected():
    """Texto vazio deve falhar antes do provider."""
    with pytest.raises(ValueError, match="narrator_text"):
        await generate_title("", "http://ollama", "llama3")


@pytest.mark.asyncio
async def test_ollama_unavailable_error_is_propagated():
    """Indisponibilidade não deve virar string vazia."""
    generator = AsyncMock(side_effect=OllamaUnavailableError("Ollama offline"))

    with patch(
        "app.services.metadata.generator.OllamaGenerator.generate",
        new=generator,
    ):
        with pytest.raises(OllamaUnavailableError, match="offline"):
            await generate_description("Narrated text", "http://ollama", "llama3")
