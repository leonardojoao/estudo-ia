"""Testes dos contratos e do serviço de upload YouTube."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.services.youtube.schemas import (
    ScheduleUploadInput,
    UploadInput,
    UploadOutput,
)


def test_upload_input_accepts_existing_video(tmp_path):
    """O contrato aceita um arquivo local existente."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    payload = UploadInput(video_path=str(video), title="Title")

    assert payload.video_path == str(video)
    assert payload.privacy == "public"


def test_upload_input_rejects_missing_video(tmp_path):
    """O contrato rejeita caminho inexistente antes da API remota."""
    with pytest.raises(ValidationError, match="não encontrado"):
        UploadInput(video_path=str(tmp_path / "missing.mp4"), title="Title")


def test_upload_input_enforces_title_and_privacy(tmp_path):
    """Título vazio/longo e privacidade fora do contrato são rejeitados."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    with pytest.raises(ValidationError):
        UploadInput(video_path=str(video), title="x" * 101)
    with pytest.raises(ValidationError):
        UploadInput(
            video_path=str(video),
            title="Title",
            privacy="invalid",
        )


def test_schedule_upload_requires_publish_at(tmp_path):
    """Uploads agendados devem possuir uma data."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")

    with pytest.raises(ValidationError):
        ScheduleUploadInput(video_path=str(video), title="Title")

    scheduled = ScheduleUploadInput(
        video_path=str(video),
        title="Title",
        publish_at=datetime.now(timezone.utc),
    )
    assert scheduled.publish_at is not None


def test_upload_output_contains_video_url():
    """O resultado expõe o ID e a URL pública."""
    output = UploadOutput(
        video_id="video-id",
        youtube_url="https://www.youtube.com/watch?v=video-id",
    )

    assert output.video_id == "video-id"
