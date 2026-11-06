"""Geração e execução de cortes de vídeo."""

import asyncio
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import ffmpeg

from app.core.exceptions import FFmpegError

from .schemas import ClipSpec, VideoFile


def _validate_clip_options(
    videos: list[VideoFile],
    total_duration_needed: float,
    min_clip: int,
    max_clip: int,
) -> None:
    """Valida os parâmetros usados para gerar os cortes."""
    if not videos:
        raise ValueError("videos não pode ser vazio")
    if total_duration_needed <= 0:
        raise ValueError("total_duration_needed deve ser maior que zero")
    if min_clip <= 0 or max_clip <= 0 or min_clip > max_clip:
        raise ValueError("min_clip e max_clip devem ser positivos e válidos")


async def generate_clip_specs(
    videos: list[VideoFile],
    total_duration_needed: float,
    min_clip: int = 3,
    max_clip: int = 6,
) -> list[ClipSpec]:
    """Gera cortes aleatórios que cobrem a duração necessária."""
    _validate_clip_options(videos, total_duration_needed, min_clip, max_clip)
    if max(video.duration_seconds for video in videos) <= 0:
        raise ValueError("videos não possuem duração utilizável")

    specs: list[ClipSpec] = []
    remaining = total_duration_needed
    clip_index = 0
    while remaining > 0:
        minimum_duration = min(min_clip, remaining)
        candidates = [
            video for video in videos if video.duration_seconds >= minimum_duration
        ]
        if not candidates:
            raise ValueError(
                "nenhum vídeo possui duração suficiente para o próximo corte"
            )

        video = random.choice(candidates)
        upper_duration = min(max_clip, remaining, video.duration_seconds)
        if upper_duration < minimum_duration:
            continue
        duration = (
            remaining
            if remaining < min_clip
            else random.uniform(min_clip, upper_duration)
        )
        max_start = video.duration_seconds - duration
        start = random.uniform(0, max_start) if max_start > 0 else 0.0
        specs.append(
            ClipSpec(
                source_video=video.path,
                start_seconds=start,
                duration_seconds=duration,
                clip_index=clip_index,
            )
        )
        remaining -= duration
        clip_index += 1
    return specs


def _run_ffmpeg_cut(spec: ClipSpec, output_path: str) -> str:
    """Executa um corte FFmpeg em processo separado."""
    try:
        (
            ffmpeg.input(spec.source_video, ss=spec.start_seconds)
            .output(
                output_path,
                t=spec.duration_seconds,
                vcodec="copy",
                acodec="copy",
            )
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as exc:
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "FFmpeg não informou detalhes da falha") from exc
    return output_path


async def cut_clip(spec: ClipSpec, output_dir: str) -> str:
    """Executa um corte e retorna o caminho do arquivo gerado."""
    if spec.duration_seconds <= 0:
        raise ValueError("duration_seconds deve ser maior que zero")

    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)
    source_stem = Path(spec.source_video).stem
    output_path = output_folder / f"clip_{spec.clip_index:04d}_{source_stem}.mp4"
    loop = asyncio.get_running_loop()
    executor = ProcessPoolExecutor(max_workers=1)
    try:
        return await loop.run_in_executor(
            executor,
            _run_ffmpeg_cut,
            spec,
            str(output_path),
        )
    except (RuntimeError, ffmpeg.Error) as exc:
        raise FFmpegError(f"Falha ao cortar vídeo: {exc}") from exc
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
