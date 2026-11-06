"""Schemas das configurações e integrações disponíveis."""

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator, model_validator


class SettingsResponse(BaseModel):
    """Mapa de configurações persistidas."""

    data: dict[str, str]


class SettingsUpdate(BaseModel):
    """Atualização parcial das configurações suportadas."""

    model_config = {"extra": "forbid"}

    ollama_url: AnyHttpUrl | None = None
    ollama_model: str | None = Field(default=None, min_length=1)
    videos_folder: str | None = None
    tts_voice: str | None = Field(default=None, min_length=1)
    default_dimension: str | None = None
    clip_min_duration: int | None = Field(default=None, gt=0)
    clip_max_duration: int | None = Field(default=None, gt=0)

    @field_validator("default_dimension")
    @classmethod
    def validate_dimension(cls, value: str | None) -> str | None:
        """Aceita apenas dimensões suportadas pelo produto."""
        if value is not None and value not in {"16:9", "9:16"}:
            raise ValueError("default_dimension deve ser 16:9 ou 9:16")
        return value

    @model_validator(mode="after")
    def validate_clip_range(self) -> "SettingsUpdate":
        """Impede uma faixa de clipes com limite máximo menor que o mínimo."""
        if (
            self.clip_min_duration is not None
            and self.clip_max_duration is not None
            and self.clip_max_duration < self.clip_min_duration
        ):
            raise ValueError(
                "clip_max_duration deve ser maior ou igual a clip_min_duration"
            )
        return self

    def as_dict(self) -> dict[str, str]:
        """Converte apenas os campos enviados para persistência."""
        return {
            key: str(value)
            for key, value in self.model_dump(exclude_unset=True).items()
            if value is not None
        }


class OllamaModel(BaseModel):
    """Modelo disponível na instância Ollama."""

    name: str


class TTSVoice(BaseModel):
    """Voz disponível para síntese."""

    name: str
    locale: str = "en"
