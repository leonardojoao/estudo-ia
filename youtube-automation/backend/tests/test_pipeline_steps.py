"""Testes dos contratos das etapas do pipeline."""

import pytest
from pydantic import ValidationError

from app.pipeline.steps import PIPELINE_STEPS, STEP_METADATA, PipelineStep, StepMeta


def test_pipeline_steps_keep_documented_order():
    assert PIPELINE_STEPS == tuple(PipelineStep)
    assert [step.value for step in PIPELINE_STEPS] == [
        "text_generation",
        "audio_generation",
        "audio_verification",
        "video_selection",
        "video_cutting",
        "video_sequencing",
        "video_composition",
        "metadata_generation",
        "upload",
    ]


def test_step_metadata_weights_sum_to_one_hundred():
    assert set(STEP_METADATA) == set(PipelineStep)
    assert sum(meta.weight for meta in STEP_METADATA.values()) == 100
    assert all(meta.name and meta.weight > 0 for meta in STEP_METADATA.values())


def test_step_metadata_is_immutable():
    with pytest.raises(ValidationError):
        StepMeta(name="Etapa", weight=1).weight = 2
