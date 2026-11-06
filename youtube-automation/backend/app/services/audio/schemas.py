"""Contratos da geração de áudio."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class AudioGenInput(BaseModel):
    """Entrada validada para a síntese de voz."""

    text: str = Field(min_length=1)
    voice: str = Field(default="en-US-JennyNeural", min_length=1)
    target_duration_seconds: float | None = Field(default=None, gt=0)
    rate: str = "+0%"
    output_path: str

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, value: str) -> str:
        """Aceita somente caminhos de arquivo, nunca diretórios."""
        if not value.strip() or Path(value).name in {"", ".", ".."}:
            raise ValueError("output_path deve apontar para um arquivo")
        return value


class AudioGenOutput(BaseModel):
    """Resultado da síntese com duração medida no arquivo gerado."""

    file_path: str
    actual_duration_seconds: float = Field(gt=0)
    target_duration_seconds: float | None
    within_tolerance: bool
    voice: str

    @model_validator(mode="after")
    def calculate_tolerance(self) -> "AudioGenOutput":
        """Calcula a tolerância de 10% quando há duração alvo."""
        if self.target_duration_seconds is None:
            self.within_tolerance = True
        else:
            difference = abs(
                self.actual_duration_seconds - self.target_duration_seconds
            )
            self.within_tolerance = difference / self.target_duration_seconds <= 0.10
        return self
