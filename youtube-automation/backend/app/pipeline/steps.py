"""Definições das etapas do pipeline e seus pesos de progresso."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class PipelineStep(str, Enum):
    """Etapas executadas pelo pipeline, na ordem padrão."""

    TEXT_GENERATION = "text_generation"
    AUDIO_GENERATION = "audio_generation"
    AUDIO_VERIFICATION = "audio_verification"
    VIDEO_SELECTION = "video_selection"
    VIDEO_CUTTING = "video_cutting"
    VIDEO_SEQUENCING = "video_sequencing"
    VIDEO_COMPOSITION = "video_composition"
    METADATA_GENERATION = "metadata_generation"
    UPLOAD = "upload"


class StepMeta(BaseModel):
    """Metadados imutáveis de uma etapa do pipeline."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    weight: int = Field(gt=0)


PIPELINE_STEPS = tuple(PipelineStep)

STEP_METADATA: dict[PipelineStep, StepMeta] = {
    PipelineStep.TEXT_GENERATION: StepMeta(name="Geração de Texto", weight=10),
    PipelineStep.AUDIO_GENERATION: StepMeta(name="Geração de Áudio", weight=10),
    PipelineStep.AUDIO_VERIFICATION: StepMeta(
        name="Verificação de Áudio",
        weight=5,
    ),
    PipelineStep.VIDEO_SELECTION: StepMeta(name="Seleção de Vídeos", weight=15),
    PipelineStep.VIDEO_CUTTING: StepMeta(name="Corte de Vídeos", weight=15),
    PipelineStep.VIDEO_SEQUENCING: StepMeta(name="Sequenciamento", weight=10),
    PipelineStep.VIDEO_COMPOSITION: StepMeta(name="Composição de Vídeo", weight=15),
    PipelineStep.METADATA_GENERATION: StepMeta(
        name="Geração de Metadata",
        weight=10,
    ),
    PipelineStep.UPLOAD: StepMeta(name="Upload", weight=10),
}
