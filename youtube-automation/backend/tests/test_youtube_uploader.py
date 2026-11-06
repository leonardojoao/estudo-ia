"""Testes dos contratos e do serviço de upload YouTube."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from googleapiclient.errors import HttpError

from app.core.exceptions import OAuthError, YouTubeAPIError
from app.models.account import YouTubeAccount
from pydantic import ValidationError

from app.services.youtube.schemas import (
    ScheduleUploadInput,
    UploadInput,
    UploadOutput,
)
from app.services.youtube.uploader import upload_video


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


@pytest.mark.asyncio
async def test_upload_video_uses_resumable_chunks_and_reports_progress(
    monkeypatch,
    tmp_path,
):
    """Upload completo deve usar chunks resumable e reportar percentual."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    request = Mock()
    request.next_chunk.side_effect = [
        (Mock(progress=Mock(return_value=0.5)), None),
        (Mock(progress=Mock(return_value=1.0)), {"id": "video-id"}),
    ]
    service = Mock()
    service.videos.return_value.insert.return_value = request
    media = Mock()
    media_factory = Mock(return_value=media)
    monkeypatch.setattr(
        "app.services.youtube.uploader.build", Mock(return_value=service)
    )
    monkeypatch.setattr(
        "app.services.youtube.uploader.MediaFileUpload",
        media_factory,
    )
    monkeypatch.setattr(
        "app.services.youtube.uploader.refresh_token_if_expired",
        AsyncMock(return_value=Mock()),
    )
    progress = []

    output = await upload_video(
        YouTubeAccount(name="Channel", channel_id="channel"),
        str(video),
        "Title",
        "Description",
        progress_callback=progress.append,
    )

    assert output == "video-id"
    assert progress == [50, 100]
    assert media_factory.call_args.kwargs["resumable"] is True
    assert media_factory.call_args.kwargs["chunksize"] == 1024 * 1024


@pytest.mark.asyncio
async def test_scheduled_upload_forces_private_and_publish_at(
    monkeypatch,
    tmp_path,
):
    """Agendamento deve enviar private e publishAt."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    request = Mock()
    request.next_chunk.return_value = (None, {"id": "scheduled-id"})
    service = Mock()
    service.videos.return_value.insert.return_value = request
    monkeypatch.setattr(
        "app.services.youtube.uploader.build", Mock(return_value=service)
    )
    monkeypatch.setattr(
        "app.services.youtube.uploader.MediaFileUpload",
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        "app.services.youtube.uploader.refresh_token_if_expired",
        AsyncMock(return_value=Mock()),
    )

    await upload_video(
        YouTubeAccount(name="Channel", channel_id="channel"),
        str(video),
        "Title",
        "Description",
        privacy="public",
        publish_at=datetime(2030, 1, 2, 3, 4, tzinfo=timezone.utc),
    )

    body = service.videos.return_value.insert.call_args.kwargs["body"]
    assert body["status"] == {
        "privacyStatus": "private",
        "publishAt": "2030-01-02T03:04:00Z",
    }


@pytest.mark.asyncio
async def test_quota_error_has_recovery_guidance(monkeypatch, tmp_path):
    """Quota excedida deve gerar mensagem orientada ao reagendamento."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    response = Mock(status=403)
    error = HttpError(
        response,
        b'{"error":{"message":"Quota exceeded","errors":[{"reason":"quotaExceeded"}]}}',
    )
    request = Mock()
    request.next_chunk.side_effect = error
    service = Mock()
    service.videos.return_value.insert.return_value = request
    monkeypatch.setattr(
        "app.services.youtube.uploader.build", Mock(return_value=service)
    )
    monkeypatch.setattr(
        "app.services.youtube.uploader.MediaFileUpload",
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        "app.services.youtube.uploader.refresh_token_if_expired",
        AsyncMock(return_value=Mock()),
    )

    with pytest.raises(YouTubeAPIError, match="01:00 PT"):
        await upload_video(
            YouTubeAccount(name="Channel", channel_id="channel"),
            str(video),
            "Title",
            "Description",
        )


@pytest.mark.asyncio
async def test_refresh_failure_deactivates_persisted_account(monkeypatch, tmp_path):
    """Falha na renovação deve desativar uma conta persistida."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        db.query(YouTubeAccount).filter_by(
            channel_id="channel-refresh-failure"
        ).delete()
        db.commit()
        account = YouTubeAccount(
            name="Channel",
            channel_id="channel-refresh-failure",
            credentials="encrypted-secret",
        )
        db.add(account)
        db.commit()
        db.flush()
        account_id = account.id
        monkeypatch.setattr(
            "app.services.youtube.uploader.refresh_token_if_expired",
            AsyncMock(side_effect=OAuthError("refresh failed")),
        )

        with pytest.raises(YouTubeAPIError, match="renovar"):
            await upload_video(
                account,
                str(video),
                "Title",
                "Description",
            )
        assert db.get(YouTubeAccount, account_id).is_active is False
