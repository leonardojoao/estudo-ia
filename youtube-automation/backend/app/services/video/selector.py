"""Descoberta e seleção de vídeos-fonte."""

import asyncio
import logging
import random
from pathlib import Path
from typing import Any

import ffmpeg
from pydantic import ValidationError

from app.core.exceptions import InsufficientVideosError

from .schemas import VideoFile

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
MINIMUM_VIDEO_DURATION_SECONDS = 6.0


def _probe_video(path: Path) -> VideoFile:
    """Extrai metadados de vídeo por meio do ffprobe."""
    metadata: dict[str, Any] = ffmpeg.probe(str(path))
    streams = metadata.get("streams", [])
    video_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise ValueError("arquivo não possui stream de vídeo")

    duration_value = metadata.get("format", {}).get("duration")
    if duration_value is None:
        duration_value = video_stream.get("duration")

    return VideoFile(
        path=str(path),
        duration_seconds=float(duration_value),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
    )


async def scan_videos_folder(folder: str) -> list[VideoFile]:
    """Lê uma pasta e extrai duração e resolução dos vídeos suportados."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return []

    videos: list[VideoFile] = []
    for path in sorted(folder_path.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            video = await asyncio.to_thread(_probe_video, path)
        except (
            ffmpeg.Error,
            KeyError,
            OSError,
            TypeError,
            ValueError,
            ValidationError,
        ) as exc:
            logger.warning("Não foi possível analisar o vídeo %s: %s", path, exc)
            continue
        videos.append(video)
    return videos


async def select_videos_for_duration(
    folder: str,
    required_duration: float,
    safety_margin: float = 0.10,
) -> list[VideoFile]:
    """Seleciona vídeos aleatoriamente até cobrir a duração necessária."""
    if required_duration <= 0:
        raise ValueError("required_duration deve ser maior que zero")
    if safety_margin < 0:
        raise ValueError("safety_margin não pode ser negativo")

    videos = await scan_videos_folder(folder)
    eligible = [
        video
        for video in videos
        if video.duration_seconds >= MINIMUM_VIDEO_DURATION_SECONDS
    ]
    target_duration = required_duration * (1 + safety_margin)
    available_duration = sum(video.duration_seconds for video in eligible)
    if not eligible:
        raise InsufficientVideosError(
            "Não há vídeos elegíveis: "
            f"duração disponível {available_duration:.2f}s, "
            f"necessária {target_duration:.2f}s"
        )

    selected: list[VideoFile] = []
    selected_duration = 0.0
    while selected_duration < target_duration:
        random.shuffle(eligible)
        for video in eligible:
            selected.append(video)
            selected_duration += video.duration_seconds
            if selected_duration >= target_duration:
                break
    return selected
