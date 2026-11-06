"""Estado acumulado e contratos de entrada do pipeline."""

from typing import Any

from pydantic import BaseModel, Field, TypeAdapter

from app.schemas.job import JobConfig
from app.services.video.schemas import ClipSpec, SequencedClip, VideoFile

from .steps import PipelineStep


class JobState(BaseModel):
    """Resultados acumulados de um job durante o processamento."""

    job_id: int = Field(gt=0)
    config: JobConfig
    generated_text: str | None = None
    audio_path: str | None = None
    audio_duration: float | None = Field(default=None, gt=0)
    selected_videos: list[VideoFile] | None = None
    clip_specs: list[ClipSpec] | None = None
    sequenced_clips: list[SequencedClip] | None = None
    composed_video_path: str | None = None
    video_title: str | None = None
    video_description: str | None = None

    def to_step_input(self, step: PipelineStep) -> dict[str, Any]:
        """Retorna somente os dados disponíveis necessários para uma etapa."""
        if not isinstance(step, PipelineStep):
            raise ValueError(f"Etapa inválida: {step!r}")

        inputs: dict[PipelineStep, dict[str, Any]] = {
            PipelineStep.TEXT_GENERATION: {
                "config": self.config.model_dump(mode="json"),
            },
            PipelineStep.AUDIO_GENERATION: {
                "text": self.generated_text,
                "voice": self.config.tts_voice,
                "target_duration_seconds": self.config.target_audio_duration,
            },
            PipelineStep.AUDIO_VERIFICATION: {
                "audio_path": self.audio_path,
                "audio_duration": self.audio_duration,
            },
            PipelineStep.VIDEO_SELECTION: {
                "audio_duration": self.audio_duration,
                "config": self.config.model_dump(mode="json"),
            },
            PipelineStep.VIDEO_CUTTING: {
                "selected_videos": self._dump_value(self.selected_videos),
                "audio_duration": self.audio_duration,
                "config": self.config.model_dump(mode="json"),
            },
            PipelineStep.VIDEO_SEQUENCING: {
                "clip_specs": self._dump_value(self.clip_specs),
            },
            PipelineStep.VIDEO_COMPOSITION: {
                "sequenced_clips": self._dump_value(self.sequenced_clips),
                "audio_path": self.audio_path,
                "config": self.config.model_dump(mode="json"),
            },
            PipelineStep.METADATA_GENERATION: {
                "generated_text": self.generated_text,
            },
            PipelineStep.UPLOAD: {
                "composed_video_path": self.composed_video_path,
                "video_title": self.video_title,
                "video_description": self.video_description,
            },
        }
        return {key: value for key, value in inputs[step].items() if value is not None}

    def save_step_output(
        self,
        step: PipelineStep,
        output: dict[str, Any],
    ) -> None:
        """Valida e incorpora o output de uma etapa ao estado."""
        if not isinstance(step, PipelineStep):
            raise ValueError(f"Etapa inválida: {step!r}")
        if not isinstance(output, dict):
            raise ValueError("O output da etapa deve ser um dicionário")

        handlers = {
            PipelineStep.TEXT_GENERATION: self._save_text_output,
            PipelineStep.AUDIO_GENERATION: self._save_audio_output,
            PipelineStep.AUDIO_VERIFICATION: self._save_audio_output,
            PipelineStep.VIDEO_SELECTION: self._save_video_selection_output,
            PipelineStep.VIDEO_CUTTING: self._save_clip_output,
            PipelineStep.VIDEO_SEQUENCING: self._save_sequence_output,
            PipelineStep.VIDEO_COMPOSITION: self._save_composition_output,
            PipelineStep.METADATA_GENERATION: self._save_metadata_output,
            PipelineStep.UPLOAD: self._save_upload_output,
        }
        handlers[step](output)

    @staticmethod
    def _dump_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, list):
            return [item.model_dump(mode="json") for item in value]
        return value.model_dump(mode="json")

    @staticmethod
    def _ensure_keys(
        output: dict[str, Any],
        allowed: set[str],
    ) -> None:
        unknown = set(output) - allowed
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Output contém campos desconhecidos: {names}")

    def _save_text_output(self, output: dict[str, Any]) -> None:
        self._ensure_keys(output, {"text", "generated_text"})
        text = output.get("text", output.get("generated_text"))
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Output de texto deve conter texto não vazio")
        self.generated_text = text

    def _save_audio_output(self, output: dict[str, Any]) -> None:
        self._ensure_keys(
            output,
            {
                "file_path",
                "actual_duration_seconds",
                "audio_path",
                "audio_duration",
            },
        )
        path = output.get("file_path", output.get("audio_path"))
        duration = output.get(
            "actual_duration_seconds",
            output.get("audio_duration"),
        )
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Output de áudio deve conter caminho válido")
        if duration is None:
            raise ValueError("Output de áudio deve conter duração")
        self.audio_path = path
        self.audio_duration = duration

    def _save_video_selection_output(self, output: dict[str, Any]) -> None:
        self._ensure_keys(output, {"selected_videos"})
        videos = TypeAdapter(list[VideoFile]).validate_python(
            output.get("selected_videos")
        )
        self.selected_videos = videos

    def _save_clip_output(self, output: dict[str, Any]) -> None:
        self._ensure_keys(output, {"clip_specs"})
        self.clip_specs = TypeAdapter(list[ClipSpec]).validate_python(
            output.get("clip_specs")
        )

    def _save_sequence_output(self, output: dict[str, Any]) -> None:
        self._ensure_keys(output, {"sequenced_clips"})
        self.sequenced_clips = TypeAdapter(list[SequencedClip]).validate_python(
            output.get("sequenced_clips")
        )

    def _save_composition_output(self, output: dict[str, Any]) -> None:
        self._ensure_keys(output, {"output_path", "composed_video_path"})
        path = output.get("output_path", output.get("composed_video_path"))
        if not isinstance(path, str) or not path.strip():
            raise ValueError("Output de composição deve conter caminho válido")
        self.composed_video_path = path

    def _save_metadata_output(self, output: dict[str, Any]) -> None:
        self._ensure_keys(
            output,
            {"title", "description", "video_title", "video_description"},
        )
        title = output.get("title", output.get("video_title"))
        description = output.get("description", output.get("video_description"))
        if not isinstance(title, str) or not title.strip():
            raise ValueError("Output de metadata deve conter título")
        if not isinstance(description, str):
            raise ValueError("Output de metadata deve conter descrição")
        self.video_title = title
        self.video_description = description

    @staticmethod
    def _save_upload_output(output: dict[str, Any]) -> None:
        JobState._ensure_keys(output, set())
