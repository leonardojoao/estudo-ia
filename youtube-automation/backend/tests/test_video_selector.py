"""Testes do selector de vídeos."""

from unittest.mock import AsyncMock, Mock

import ffmpeg
import pytest

from app.core.exceptions import InsufficientVideosError
from app.services.video.schemas import VideoFile
from app.services.video.selector import (
    MINIMUM_VIDEO_DURATION_SECONDS,
    scan_videos_folder,
    select_videos_for_duration,
)


def _probe_result(duration: float = 12.0) -> dict:
    return {
        "format": {"duration": str(duration)},
        "streams": [
            {
                "codec_type": "video",
                "width": 1920,
                "height": 1080,
            }
        ],
    }


@pytest.mark.asyncio
async def test_scan_returns_video_metadata(monkeypatch, tmp_path) -> None:
    """A varredura deve converter o resultado do ffprobe em VideoFile."""
    source = tmp_path / "source.mp4"
    source.touch()
    monkeypatch.setattr(
        "app.services.video.selector.ffmpeg.probe", lambda _: _probe_result()
    )

    videos = await scan_videos_folder(str(tmp_path))

    assert videos == [
        VideoFile(
            path=str(source),
            duration_seconds=12,
            width=1920,
            height=1080,
        )
    ]


@pytest.mark.asyncio
async def test_scan_ignores_unsupported_and_invalid_files(
    monkeypatch, tmp_path
) -> None:
    """Arquivos não suportados e probes inválidos não interrompem a varredura."""
    (tmp_path / "notes.txt").touch()
    invalid = tmp_path / "broken.mp4"
    valid = tmp_path / "valid.mkv"
    invalid.touch()
    valid.touch()

    def probe(path: str) -> dict:
        if path.endswith("broken.mp4"):
            raise ffmpeg.Error("ffprobe", b"", b"invalid media")
        return _probe_result()

    monkeypatch.setattr("app.services.video.selector.ffmpeg.probe", probe)

    videos = await scan_videos_folder(str(tmp_path))

    assert [video.path for video in videos] == [str(valid)]


@pytest.mark.asyncio
async def test_scan_missing_folder_returns_empty(tmp_path) -> None:
    """Uma pasta inexistente deve resultar em lista vazia."""
    videos = await scan_videos_folder(str(tmp_path / "missing"))

    assert videos == []


@pytest.mark.asyncio
async def test_select_applies_margin_and_repeats(monkeypatch) -> None:
    """A seleção deve repetir fontes quando uma passagem não basta."""
    videos = [
        VideoFile(path="a.mp4", duration_seconds=7, width=1920, height=1080),
        VideoFile(path="b.mp4", duration_seconds=8, width=1920, height=1080),
    ]
    monkeypatch.setattr(
        "app.services.video.selector.scan_videos_folder",
        AsyncMock(return_value=videos),
    )
    random_stub = Mock()
    monkeypatch.setattr("app.services.video.selector.random", random_stub)

    selected = await select_videos_for_duration("videos", 20, safety_margin=0.10)

    assert sum(video.duration_seconds for video in selected) >= 22
    assert len(selected) > len(videos)
    assert random_stub.shuffle.call_count >= 2


@pytest.mark.asyncio
async def test_select_ignores_short_videos(monkeypatch) -> None:
    """Vídeos abaixo de seis segundos não devem ser selecionados."""
    videos = [
        VideoFile(
            path="short.mp4",
            duration_seconds=MINIMUM_VIDEO_DURATION_SECONDS - 0.1,
            width=1920,
            height=1080,
        ),
        VideoFile(path="valid.mp4", duration_seconds=6, width=1920, height=1080),
    ]
    monkeypatch.setattr(
        "app.services.video.selector.scan_videos_folder",
        AsyncMock(return_value=videos),
    )

    selected = await select_videos_for_duration("videos", 5, safety_margin=0)

    assert {video.path for video in selected} == {"valid.mp4"}


@pytest.mark.asyncio
async def test_select_raises_when_no_video_is_eligible(monkeypatch) -> None:
    """A ausência de vídeos elegíveis deve produzir erro de domínio."""
    monkeypatch.setattr(
        "app.services.video.selector.scan_videos_folder",
        AsyncMock(return_value=[]),
    )

    with pytest.raises(InsufficientVideosError, match="disponível.*necessária"):
        await select_videos_for_duration("videos", 10)


@pytest.mark.asyncio
async def test_select_rejects_non_positive_duration(monkeypatch) -> None:
    """A duração requerida precisa ser positiva."""
    with pytest.raises(ValueError, match="required_duration"):
        await select_videos_for_duration("videos", 0)
