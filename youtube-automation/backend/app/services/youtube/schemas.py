"""Contratos de entrada e saída do uploader YouTube."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PrivacyStatus = Literal["public", "private", "unlisted"]


class UploadInput(BaseModel):
    """Dados necessários para um upload imediato ou agendado."""

    video_path: str
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=500)
    category_id: str = Field(default="22", min_length=1, max_length=10)
    privacy: PrivacyStatus = "public"
    publish_at: datetime | None = None

    @field_validator("video_path")
    @classmethod
    def validate_video_path(cls, value: str) -> str:
        """Garante que o arquivo de vídeo exista e seja regular."""
        path = Path(value)
        if not path.is_file():
            raise ValueError("Arquivo de vídeo não encontrado")
        return str(path)


class UploadOutput(BaseModel):
    """Resultado público de um upload concluído."""

    video_id: str = Field(min_length=1)
    youtube_url: str


class ScheduleUploadInput(UploadInput):
    """Dados de upload que obrigatoriamente possuem agendamento."""

    publish_at: datetime
