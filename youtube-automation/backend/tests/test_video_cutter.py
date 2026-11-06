"""Testes do cutter de vídeos."""

from concurrent.futures import Future
from unittest.mock import Mock

import pytest

from app.core.exceptions import FFmpegError
from app.services.video.cutter import (
    _run_ffmpeg_cut,
    cut_clip,
    generate_clip_specs,
)
from app.services.video.schemas import ClipSpec, VideoFile


def _video(path: str, duration: float = 20) -> VideoFile:
    return VideoFile(path=path, duration_seconds=duration, width=1920, height=1080)


@pytest.mark.asyncio
async def test_generate_specs_cover_duration_without_exceeding_source(monkeypatch):
    """Os specs devem cobrir a duração sem ultrapassar as fontes."""
    monkeypatch.setattr(
        "app.services.video.cutter.random.choice", lambda values: values[0]
    )
    monkeypatch.setattr(
        "app.services.video.cutter.random.uniform",
        lambda lower, upper: upper,
    )

    specs = await generate_clip_specs([_video("source.mp4")], 10)

    assert sum(spec.duration_seconds for spec in specs) == pytest.approx(10)
    assert all(spec.start_seconds + spec.duration_seconds <= 20 for spec in specs)
    assert [spec.clip_index for spec in specs] == list(range(len(specs)))
    assert all(3 <= spec.duration_seconds <= 6 for spec in specs)


@pytest.mark.asyncio
async def test_generate_specs_reduces_final_clip(monkeypatch):
    """O último corte pode ser menor que o mínimo para fechar a duração."""
    monkeypatch.setattr(
        "app.services.video.cutter.random.choice", lambda values: values[0]
    )
    monkeypatch.setattr(
        "app.services.video.cutter.random.uniform",
        lambda lower, upper: upper,
    )

    specs = await generate_clip_specs([_video("source.mp4")], 7)

    assert sum(spec.duration_seconds for spec in specs) == pytest.approx(7)
    assert specs[-1].duration_seconds == pytest.approx(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("videos", "duration", "min_clip", "max_clip"),
    [
        ([], 10, 3, 6),
        ([_video("source.mp4")], 0, 3, 6),
        ([_video("source.mp4")], 10, 0, 6),
        ([_video("source.mp4")], 10, 6, 3),
    ],
)
async def test_generate_specs_rejects_invalid_options(
    videos,
    duration,
    min_clip,
    max_clip,
):
    """Parâmetros inválidos devem falhar antes da geração."""
    with pytest.raises(ValueError):
        await generate_clip_specs(videos, duration, min_clip, max_clip)


class _ExecutorStub:
    """Executor síncrono controlável para testar o worker assíncrono."""

    def __init__(self, max_workers):
        self.max_workers = max_workers

    def submit(self, function, *args):
        future = Future()
        try:
            future.set_result(function(*args))
        except Exception as exc:
            future.set_exception(exc)
        return future

    def shutdown(self, wait=True, cancel_futures=True):
        return None


@pytest.mark.asyncio
async def test_cut_clip_builds_expected_output(monkeypatch, tmp_path):
    """O corte deve montar nome, diretório e parâmetros esperados."""
    spec = ClipSpec(
        source_video="source video.mp4",
        start_seconds=2.5,
        duration_seconds=4,
        clip_index=3,
    )
    worker = Mock(return_value=str(tmp_path / "clip_0003_source video.mp4"))
    monkeypatch.setattr("app.services.video.cutter._run_ffmpeg_cut", worker)
    monkeypatch.setattr(
        "app.services.video.cutter.ProcessPoolExecutor",
        _ExecutorStub,
    )

    output = await cut_clip(spec, str(tmp_path))

    assert output.endswith("clip_0003_source video.mp4")
    worker.assert_called_once()


@pytest.mark.asyncio
async def test_cut_clip_converts_ffmpeg_failure(monkeypatch, tmp_path):
    """Falhas de execução devem expor FFmpegError."""
    spec = ClipSpec(
        source_video="source.mp4",
        start_seconds=0,
        duration_seconds=3,
        clip_index=0,
    )
    monkeypatch.setattr(
        "app.services.video.cutter._run_ffmpeg_cut",
        Mock(side_effect=RuntimeError("stderr failure")),
    )
    monkeypatch.setattr(
        "app.services.video.cutter.ProcessPoolExecutor",
        _ExecutorStub,
    )

    with pytest.raises(FFmpegError, match="stderr failure"):
        await cut_clip(spec, str(tmp_path))


def test_run_ffmpeg_cut_uses_fast_seek_and_copy_codecs(monkeypatch, tmp_path):
    """O worker deve montar o comando FFmpeg definido pelo contrato."""
    spec = ClipSpec(
        source_video="source.mp4",
        start_seconds=2.5,
        duration_seconds=4,
        clip_index=0,
    )
    stream = Mock()
    stream.output.return_value = stream
    stream.overwrite_output.return_value = stream
    input_mock = Mock(return_value=stream)
    monkeypatch.setattr("app.services.video.cutter.ffmpeg.input", input_mock)

    output = _run_ffmpeg_cut(spec, str(tmp_path / "clip.mp4"))

    assert output.endswith("clip.mp4")
    input_mock.assert_called_once_with("source.mp4", ss=2.5)
    stream.output.assert_called_once_with(
        str(tmp_path / "clip.mp4"),
        t=4,
        vcodec="copy",
        acodec="copy",
    )
    stream.overwrite_output.assert_called_once_with()
    stream.run.assert_called_once_with(capture_stdout=True, capture_stderr=True)
