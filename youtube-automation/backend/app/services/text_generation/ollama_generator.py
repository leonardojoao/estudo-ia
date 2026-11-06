"""Implementação do provedor de texto usando Ollama."""

from time import perf_counter
from typing import Any

import httpx
import ollama

from app.core.exceptions import OllamaUnavailableError

from .base import TextGenerator
from .schemas import TextGenInput, TextGenOutput


class OllamaGenerator(TextGenerator):
    """Gera textos através de uma instância Ollama configurável."""

    def __init__(self, ollama_url: str) -> None:
        self.ollama_url = ollama_url.rstrip("/")

    def _client(self) -> ollama.AsyncClient:
        return ollama.AsyncClient(host=self.ollama_url, timeout=5.0)

    @staticmethod
    def _value(response: Any, key: str, default: Any = None) -> Any:
        if isinstance(response, dict):
            return response.get(key, default)
        return getattr(response, key, default)

    async def generate(self, input: TextGenInput) -> TextGenOutput:
        """Executa uma geração e normaliza a resposta do Ollama."""
        started = perf_counter()
        try:
            response = await self._client().generate(
                model=input.model,
                prompt=input.prompt,
                options={
                    "num_predict": input.max_tokens,
                    "temperature": input.temperature,
                },
            )
        except (httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
            raise OllamaUnavailableError(
                "Ollama não está disponível",
                details={"url": self.ollama_url},
            ) from exc

        text = str(self._value(response, "response", "")).strip()
        if not text:
            raise OllamaUnavailableError("Ollama retornou uma resposta vazia")
        return TextGenOutput(
            text=text,
            model=input.model,
            duration_ms=round((perf_counter() - started) * 1000),
            tokens_used=self._value(response, "eval_count"),
        )

    async def generate_batch(
        self,
        input: TextGenInput,
        count: int,
    ) -> list[TextGenOutput]:
        """Executa gerações em sequência para não sobrecarregar o modelo."""
        if count <= 0:
            raise ValueError("count deve ser maior que zero")
        return [await self.generate(input) for _ in range(count)]

    async def list_models(self) -> list[str]:
        """Lista modelos instalados ou retorna vazio quando Ollama está offline."""
        try:
            response = await self._client().list()
        except (httpx.ConnectError, httpx.TimeoutException, OSError):
            return []

        models = self._value(response, "models", []) or []
        names = [self._value(model, "name", "") for model in models]
        return [str(name) for name in names if name]
