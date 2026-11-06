"""Composição de clipes com áudio e dimensionamento final."""

import asyncio
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import ffmpeg

from app.core.exceptions import FFmpegError

from .schemas import VideoCompositionInput, VideoCompositionOutput


def _escape_concat_path(path: str) -> str:
    """Escapa um path para uma entrada do concat demuxer."""
    return path.replace("'", r"'\''")


def _build_concat_list(input: VideoCompositionInput, path: Path) -> None:
    """Escreve a lista ordenada de clipes para o concat demuxer."""
    clips = sorted(
        input.sequenced_clips,
        key=lambda clip: clip.sequence_position,
    )
    lines = []
    for clip in clips:
        clip_path = clip.output_path or clip.clip_spec.source_video
        lines.append(f"file '{_escape_concat_path(clip_path)}'")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _dimension_filter(dimension: str, crop_for_vertical: bool) -> str:
    """Retorna o filtergraph correspondente à dimensão final."""
    if dimension == "16:9":
        return (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
        )
    if crop_for_vertical:
        return (
            "scale=1920:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920:(iw-1080)/2:(ih-1920)/2"
        )
    return (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
    )


def _apply_dimension_filter(video_stream: Any, dimension: str, crop: bool) -> Any:
    """Aplica o filtro de escala e enquadramento ao stream de vídeo."""
    if dimension == "16:9":
        return video_stream.filter(
            "scale",
            1920,
            1080,
            force_original_aspect_ratio="decrease",
        ).filter("pad", 1920, 1080, "(ow-iw)/2", "(oh-ih)/2")
    if crop:
        return video_stream.filter(
            "scale",
            1920,
            1920,
            force_original_aspect_ratio="increase",
        ).filter("crop", 1080, 1920, "(iw-1080)/2", "(ih-1920)/2")
    return video_stream.filter(
        "scale",
        1080,
        1920,
        force_original_aspect_ratio="decrease",
    ).filter("pad", 1080, 1920, "(ow-iw)/2", "(oh-ih)/2")


def _probe_output(path: str) -> VideoCompositionOutput:
    """Lê os metadados do vídeo composto."""
    metadata: dict[str, Any] = ffmpeg.probe(path)
    streams = metadata.get("streams", [])
    video_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise ValueError("o output não possui stream de vídeo")
    duration = metadata.get("format", {}).get("duration")
    if duration is None:
        duration = video_stream.get("duration")
    if duration is None:
        raise ValueError("não foi possível ler a duração do output")
    return VideoCompositionOutput(
        output_path=path,
        duration_seconds=float(duration),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        file_size_bytes=os.path.getsize(path),
    )


def _run_compose(input_data: dict[str, Any]) -> VideoCompositionOutput:
    """Executa concatenação, filtragem, merge e probe em um processo."""
    composition = VideoCompositionInput.model_validate(input_data)
    output = Path(composition.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=str(output.parent)) as temp_dir:
            temp_path = Path(temp_dir)
            list_path = temp_path / "list.txt"
            concat_path = temp_path / "temp_video.mp4"
            _build_concat_list(composition, list_path)
            (
                ffmpeg.input(str(list_path), format="concat", safe=0)
                .output(str(concat_path), c="copy")
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            video_input = ffmpeg.input(str(concat_path))
            audio_input = ffmpeg.input(composition.audio_path)
            filtered_video = _apply_dimension_filter(
                video_input.video,
                composition.dimension,
                composition.crop_for_vertical,
            )
            (
                ffmpeg.output(
                    filtered_video,
                    audio_input.audio,
                    str(output),
                    vcodec="libx264",
                    acodec="aac",
                    shortest=None,
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return _probe_output(str(output))
    except ffmpeg.Error as exc:
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "FFmpeg não informou detalhes da falha") from exc
    except (OSError, ValueError) as exc:
        raise RuntimeError(str(exc)) from exc


async def compose_video(
    input: VideoCompositionInput,
) -> VideoCompositionOutput:
    """Compõe os clipes e o áudio em processo separado."""
    if not input.sequenced_clips:
        raise ValueError("sequenced_clips não pode ser vazio")
    loop = asyncio.get_running_loop()
    executor = ProcessPoolExecutor(max_workers=1)
    try:
        return await loop.run_in_executor(
            executor,
            _run_compose,
            input.model_dump(),
        )
    except (RuntimeError, ffmpeg.Error) as exc:
        raise FFmpegError(f"Falha ao compor vídeo: {exc}") from exc
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
