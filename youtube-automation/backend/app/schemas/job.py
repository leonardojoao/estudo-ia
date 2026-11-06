"""Schemas dos processamentos e etapas do pipeline."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobConfig(BaseModel):
    """Configuração validada de um processamento."""

    model: str = Field(default="llama3", min_length=1)
    prompt: str | None = None
    manual_text: str | None = None
    target_audio_duration: float = Field(default=60, gt=0)
    tts_voice: str = Field(default="en-US-JennyNeural", min_length=1)
    dimension: str = Field(default="16:9", pattern=r"^(16:9|9:16)$")
    account_ids: list[int] = Field(min_length=1)
    pre_generated_text: str | None = None
    pre_generated_audio_path: str | None = None
    pre_generated_audio_duration: float | None = Field(default=None, gt=0)
    pre_generated_title: str | None = None
    pre_generated_description: str | None = None

    @model_validator(mode="after")
    def validate_text_source(self) -> "JobConfig":
        """Exige uma origem de texto quando nenhum conteúdo foi pré-gerado."""
        if not any(
            (
                self.prompt,
                self.manual_text,
                self.pre_generated_text,
            )
        ):
            raise ValueError("Informe prompt, manual_text ou pre_generated_text")
        return self


class JobCreate(BaseModel):
    """Dados para criar um processamento."""

    name: str = Field(min_length=1, max_length=255)
    config: JobConfig
    scheduled_at: datetime | None = None


class JobResponse(BaseModel):
    """Resposta pública de um processamento."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    current_step: str | None
    progress: int
    output_video: str | None
    error_message: str | None
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class JobListResponse(BaseModel):
    """Resposta paginada de processamentos."""

    items: list[JobResponse]
    total: int


class JobStepResponse(BaseModel):
    """Resposta pública de uma etapa do pipeline."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    step_name: str
    status: str
    output: str | None
    log: str | None
    duration_ms: int | None
    started_at: datetime | None
    completed_at: datetime | None


class StepExecuteRequest(BaseModel):
    """Solicitação de execução isolada de uma etapa."""

    step_name: str = Field(min_length=1, max_length=100)
    input: dict = Field(default_factory=dict)
