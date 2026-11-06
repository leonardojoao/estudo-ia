"""Testes do estado acumulado do pipeline."""

import json

import pytest

from app.pipeline.state import JobState
from app.pipeline.steps import PipelineStep
from app.schemas.job import JobConfig
from app.services.video.schemas import ClipSpec, SequencedClip, VideoFile


def _config() -> JobConfig:
    return JobConfig(
        manual_text="Texto de teste",
        account_ids=[1],
        target_audio_duration=30,
    )


def _state() -> JobState:
    return JobState(job_id=1, config=_config())


def test_initial_state_serializes_to_json():
    payload = json.loads(_state().model_dump_json())
    assert payload["job_id"] == 1
    assert payload["config"]["account_ids"] == [1]
    assert payload["generated_text"] is None


def test_to_step_input_returns_only_available_inputs():
    state = _state()
    assert state.to_step_input(PipelineStep.TEXT_GENERATION)["config"]["model"] == (
        "llama3"
    )
    assert state.to_step_input(PipelineStep.AUDIO_GENERATION) == {
        "voice": "en-US-JennyNeural",
        "target_duration_seconds": 30.0,
    }
    assert state.to_step_input(PipelineStep.AUDIO_VERIFICATION) == {}


def test_to_step_input_serializes_nested_video_models():
    state = _state().model_copy(
        update={
            "selected_videos": [
                VideoFile(
                    path="source.mp4",
                    duration_seconds=10,
                    width=1920,
                    height=1080,
                )
            ],
            "clip_specs": [
                ClipSpec(
                    source_video="source.mp4",
                    start_seconds=0,
                    duration_seconds=5,
                    clip_index=0,
                )
            ],
        }
    )
    assert state.to_step_input(PipelineStep.VIDEO_CUTTING)["selected_videos"] == [
        {
            "path": "source.mp4",
            "duration_seconds": 10.0,
            "width": 1920,
            "height": 1080,
        }
    ]
    assert state.to_step_input(PipelineStep.VIDEO_SEQUENCING) == {
        "clip_specs": [
            {
                "source_video": "source.mp4",
                "start_seconds": 0.0,
                "duration_seconds": 5.0,
                "clip_index": 0,
            }
        ]
    }


def test_save_step_outputs_updates_accumulated_state():
    state = _state()
    state.save_step_output(PipelineStep.TEXT_GENERATION, {"text": "Gerado"})
    state.save_step_output(
        PipelineStep.AUDIO_GENERATION,
        {"file_path": "audio.mp3", "actual_duration_seconds": 29.5},
    )
    state.save_step_output(
        PipelineStep.VIDEO_SELECTION,
        {
            "selected_videos": [
                {
                    "path": "source.mp4",
                    "duration_seconds": 10,
                    "width": 1920,
                    "height": 1080,
                }
            ]
        },
    )
    state.save_step_output(
        PipelineStep.METADATA_GENERATION,
        {"title": "Título", "description": "Descrição"},
    )

    assert state.generated_text == "Gerado"
    assert state.audio_path == "audio.mp3"
    assert state.audio_duration == 29.5
    assert state.selected_videos[0].path == "source.mp4"
    assert state.video_title == "Título"
    assert state.video_description == "Descrição"


def test_save_step_outputs_validates_nested_outputs():
    state = _state()
    state.save_step_output(
        PipelineStep.VIDEO_SEQUENCING,
        {
            "sequenced_clips": [
                {
                    "clip_spec": {
                        "source_video": "source.mp4",
                        "start_seconds": 0,
                        "duration_seconds": 5,
                        "clip_index": 0,
                    },
                    "sequence_position": 0,
                }
            ]
        },
    )
    state.save_step_output(
        PipelineStep.VIDEO_COMPOSITION,
        {"output_path": "final.mp4"},
    )
    assert isinstance(state.sequenced_clips[0], SequencedClip)
    assert state.composed_video_path == "final.mp4"


def test_invalid_step_and_unknown_output_are_rejected():
    state = _state()
    with pytest.raises(ValueError):
        state.to_step_input("not-a-step")
    with pytest.raises(ValueError):
        state.save_step_output(PipelineStep.TEXT_GENERATION, {"unknown": "value"})
    with pytest.raises(ValueError):
        state.save_step_output(PipelineStep.UPLOAD, {"url": "https://example.test"})
