"""Testes do composer de vídeos."""

from concurrent.futures import Future
from unittest.mock import Mock

import pytest

from app.core.exceptions import FFmpegError
from app.services.video.composer import (
    _build_concat_list,
    _dimension_filter,
    _run_compose,
    compose_video,
)
from app.services.video.schemas import (
    ClipSpec,
    SequencedClip,
    VideoCompositionInput,
)


def _composition(tmp_path, *, dimension="16:9", crop=False):
    return VideoCompositionInput(
        sequenced_clips=[
            SequencedClip(
                clip_spec=ClipSpec(
                    source_video="source-a.mp4",
                    start_seconds=0,
                    duration_seconds=3,
                    clip_index=0,
                ),
                sequence_position=1,
                output_path="clip-b.mp4",
            ),
            SequencedClip(
                clip_spec=ClipSpec(
                    source_video="source-b.mp4",
                    start_seconds=0,
                    duration_seconds=3,
                    clip_index=1,
                ),
                sequence_position=0,
                output_path="clip-a.mp4",
            ),
        ],
        audio_path="audio.mp3",
        output_path=str(tmp_path / "output.mp4"),
        dimension=dimension,
        crop_for_vertical=crop,
    )


def test_build_concat_list_sorts_and_escapes_paths(tmp_path):
    """A lista deve seguir a sequência e escapar aspas simples."""
    composition = _composition(tmp_path)
    composition.sequenced_clips[0].output_path = "clip's-b.mp4"
    list_path = tmp_path / "list.txt"

    _build_concat_list(composition, list_path)

    assert list_path.read_text(encoding="utf-8") == (
        "file 'clip-a.mp4'\nfile 'clip'\\''s-b.mp4'\n"
    )


@pytest.mark.parametrize(
    ("dimension", "crop", "expected"),
    [
        ("16:9", False, "scale=1920:1080"),
        ("9:16", True, "crop=1080:1920"),
        ("9:16", False, "pad=1080:1920"),
    ],
)
def test_dimension_filter_supports_all_modes(dimension, crop, expected):
    """Cada modo deve gerar o filtro correspondente."""
    assert expected in _dimension_filter(dimension, crop)


class _ExecutorStub:
    """Executor controlável para testar delegação assíncrona."""

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
async def test_compose_video_delegates_to_process_pool(monkeypatch, tmp_path):
    """A API assíncrona deve delegar o trabalho ao executor."""
    composition = _composition(tmp_path)
    result = Mock(output_path=composition.output_path)
    worker = Mock(return_value=result)
    monkeypatch.setattr("app.services.video.composer._run_compose", worker)
    monkeypatch.setattr(
        "app.services.video.composer.ProcessPoolExecutor",
        _ExecutorStub,
    )

    output = await compose_video(composition)

    assert output is result
    worker.assert_called_once()


@pytest.mark.asyncio
async def test_compose_video_converts_worker_error(monkeypatch, tmp_path):
    """Falha do worker deve virar erro de domínio."""
    composition = _composition(tmp_path)
    monkeypatch.setattr(
        "app.services.video.composer._run_compose",
        Mock(side_effect=RuntimeError("stderr failure")),
    )
    monkeypatch.setattr(
        "app.services.video.composer.ProcessPoolExecutor",
        _ExecutorStub,
    )

    with pytest.raises(FFmpegError, match="stderr failure"):
        await compose_video(composition)


def test_run_compose_uses_concat_merge_and_probe(monkeypatch, tmp_path):
    """O worker deve executar concat, filtro, merge e probe."""
    composition = _composition(tmp_path)
    concat_stream = Mock()
    concat_stream.output.return_value = concat_stream
    concat_stream.overwrite_output.return_value = concat_stream
    video_stream = Mock()
    video_stream.filter.return_value = video_stream
    audio_stream = Mock()
    output_stream = Mock()
    output_stream.overwrite_output.return_value = output_stream
    input_mock = Mock(side_effect=[concat_stream, video_stream, audio_stream])
    output_mock = Mock(return_value=output_stream)
    probe_mock = Mock(
        return_value={
            "format": {"duration": "6"},
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                }
            ],
        }
    )
    output_path = composition.output_path
    monkeypatch.setattr("app.services.video.composer.ffmpeg.input", input_mock)
    monkeypatch.setattr("app.services.video.composer.ffmpeg.output", output_mock)
    monkeypatch.setattr("app.services.video.composer.ffmpeg.probe", probe_mock)
    monkeypatch.setattr("os.path.getsize", lambda _: 1234)

    result = _run_compose(composition.model_dump())

    assert result.width == 1920
    assert result.height == 1080
    assert result.file_size_bytes == 1234
    assert input_mock.call_args_list[0].kwargs == {"format": "concat", "safe": 0}
    output_mock.assert_called_once()
    final_kwargs = output_mock.call_args.kwargs
    assert final_kwargs["vcodec"] == "libx264"
    assert final_kwargs["acodec"] == "aac"
    assert final_kwargs["shortest"] is None
    assert output_mock.call_args.args[2] == output_path
    assert probe_mock.call_args.args == (output_path,)
