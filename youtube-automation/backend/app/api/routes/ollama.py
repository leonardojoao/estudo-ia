"""Rotas de integração e diagnóstico do Ollama."""

from fastapi import APIRouter, Depends

from app.api.deps import get_settings
from app.core.config import Settings
from app.schemas.settings import OllamaModel, TTSVoice
from app.services.text_generation.ollama_generator import OllamaGenerator

router = APIRouter(prefix="/ollama", tags=["ollama"])

VOICES = [
    TTSVoice(name="en-US-JennyNeural"),
    TTSVoice(name="en-US-GuyNeural"),
    TTSVoice(name="en-US-AriaNeural"),
    TTSVoice(name="en-US-DavisNeural"),
    TTSVoice(name="en-GB-SoniaNeural"),
    TTSVoice(name="en-GB-RyanNeural"),
]


def _generator(settings: Settings) -> OllamaGenerator:
    return OllamaGenerator(settings.ollama_url)


@router.get("/models", response_model=list[OllamaModel])
async def list_models(settings: Settings = Depends(get_settings)) -> list[OllamaModel]:
    """Retorna modelos instalados no Ollama."""
    names = await _generator(settings).list_models()
    return [OllamaModel(name=name) for name in names]


@router.get("/voices", response_model=list[TTSVoice])
async def list_voices() -> list[TTSVoice]:
    """Retorna vozes neurais em inglês suportadas pelo produto."""
    return VOICES


@router.post("/test")
async def test_connection(
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Testa a conexão sem transformar Ollama offline em erro HTTP."""
    models = await _generator(settings).list_models()
    if not models:
        return {"ok": False, "error": "Ollama indisponível ou sem modelos instalados"}
    return {"ok": True, "models": models}
