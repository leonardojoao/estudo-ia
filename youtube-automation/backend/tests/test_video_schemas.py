"""Testes dos contratos do pipeline de vídeo."""

import pytest
from pydantic import ValidationError

from app.services.video.schemas import (
    ClipSpec,
    SequencedClip,
    VideoCompositionInput,
    VideoCompositionOutput,
    VideoFile,
)


def test_video_schemas_accept_valid_composition() -> None:
    """Uma composição válida deve ser aceita."""
    clip = SequencedClip(
        clip_spec=ClipSpec(
            source_video="source.mp4",
            start_seconds=0,
            duration_seconds=4,
            clip_index=0,
        ),
        sequence_position=0,
    )
    composition = VideoCompositionInput(
        sequenced_clips=[clip],
        audio_path="audio.mp3",
        output_path="output.mp4",
        dimension="9:16",
    )

    assert composition.dimension == "9:16"


def test_video_file_rejects_non_positive_dimensions() -> None:
    """Metadados físicos inválidos devem ser rejeitados."""
    with pytest.raises(ValidationError):
        VideoFile(path="source.mp4", duration_seconds=10, width=0, height=1080)


def test_composition_rejects_unknown_dimension() -> None:
    """O pipeline deve limitar o formato a landscape ou vertical."""
    with pytest.raises(ValidationError):
        VideoCompositionInput(
            sequenced_clips=[],
            audio_path="audio.mp3",
            output_path="output.mp4",
            dimension="4:3",
        )


def test_composition_output_validates_file_size() -> None:
    """O resultado não pode reportar tamanho negativo."""
    with pytest.raises(ValidationError):
        VideoCompositionOutput(
            output_path="output.mp4",
            duration_seconds=10,
            width=1920,
            height=1080,
            file_size_bytes=-1,
        )
