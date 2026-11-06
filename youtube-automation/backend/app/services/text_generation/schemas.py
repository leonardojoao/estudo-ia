"""Contratos da geração de texto."""

from pydantic import BaseModel, Field


class TextGenInput(BaseModel):
    """Entrada validada para um provedor de texto."""

    prompt: str = Field(min_length=1)
    model: str = Field(min_length=1)
    max_tokens: int = Field(default=500, gt=0)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class TextGenOutput(BaseModel):
    """Resultado normalizado de uma geração."""

    text: str = Field(min_length=1)
    model: str
    duration_ms: int = Field(ge=0)
    tokens_used: int | None = Field(default=None, ge=0)
