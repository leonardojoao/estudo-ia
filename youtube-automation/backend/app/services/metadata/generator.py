"""Geração de título e descrição para vídeos."""

from app.services.text_generation.ollama_generator import OllamaGenerator
from app.services.text_generation.schemas import TextGenInput

DEFAULT_TITLE_PROMPT = (
    "Based on the following text, create a YouTube video title "
    "(max 100 chars): {text}"
)
DEFAULT_DESCRIPTION_PROMPT = (
    "Based on the following text, create a YouTube video description "
    "(max 5000 chars): {text}"
)


def _build_prompt(template: str, narrator_text: str) -> str:
    """Preenche o template e garante contexto quando não há placeholder."""
    if "{text}" in template:
        return template.replace("{text}", narrator_text)
    return f"{template.rstrip()}\n\nText:\n{narrator_text}"


async def _generate(
    narrator_text: str,
    ollama_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    max_length: int,
) -> str:
    """Gera texto no Ollama e aplica o limite público do resultado."""
    if not narrator_text.strip():
        raise ValueError("narrator_text não pode ser vazio")
    generator = OllamaGenerator(ollama_url)
    result = await generator.generate(
        TextGenInput(
            prompt=_build_prompt(prompt, narrator_text),
            model=model,
            max_tokens=max_tokens,
        )
    )
    return result.text.strip()[:max_length]


async def generate_title(
    narrator_text: str,
    ollama_url: str,
    model: str,
    title_prompt: str | None = None,
) -> str:
    """Gera um título limitado a 100 caracteres."""
    return await _generate(
        narrator_text,
        ollama_url,
        model,
        title_prompt or DEFAULT_TITLE_PROMPT,
        max_tokens=100,
        max_length=100,
    )


async def generate_description(
    narrator_text: str,
    ollama_url: str,
    model: str,
    description_prompt: str | None = None,
) -> str:
    """Gera uma descrição limitada a 5000 caracteres."""
    return await _generate(
        narrator_text,
        ollama_url,
        model,
        description_prompt or DEFAULT_DESCRIPTION_PROMPT,
        max_tokens=1500,
        max_length=5000,
    )
