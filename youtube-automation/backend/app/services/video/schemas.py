"""Contratos das etapas de processamento de vídeo."""

from pydantic import BaseModel, Field, field_validator


class VideoFile(BaseModel):
    """Metadados de um arquivo de vídeo."""

    path: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ClipSpec(BaseModel):
    """Especificação de um corte dentro de um vídeo."""

    source_video: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)
    clip_index: int = Field(ge=0)


class SequencedClip(BaseModel):
    """Clipe após a definição da ordem de composição."""

    clip_spec: ClipSpec
    sequence_position: int = Field(ge=0)
    output_path: str | None = None


class VideoCompositionInput(BaseModel):
    """Entrada para a composição do vídeo final."""

    sequenced_clips: list[SequencedClip] = Field(min_length=1)
    audio_path: str = Field(min_length=1)
    output_path: str = Field(min_length=1)
    dimension: str = "16:9"
    crop_for_vertical: bool = False

    @field_validator("dimension")
    @classmethod
    def validate_dimension(cls, value: str) -> str:
        """Aceita somente formatos previstos pelo produto."""
        if value not in {"16:9", "9:16"}:
            raise ValueError("dimension deve ser 16:9 ou 9:16")
        return value


class VideoCompositionOutput(BaseModel):
    """Resultado da composição do vídeo."""

    output_path: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    file_size_bytes: int = Field(ge=0)
