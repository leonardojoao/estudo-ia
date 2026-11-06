"""Testes do serviço edge-tts."""

import asyncio

import pytest
from pydantic import ValidationError

from app.services.audio.edge_tts import EdgeTTSGenerator
from app.services.audio.schemas import AudioGenInput, AudioGenOutput


def test_audio_output_calculates_ten_percent_tolerance() -> None:
    """A saída deve marcar duração dentro ou fora da margem de 10%."""
    inside = AudioGenOutput(
        file_path="audio.mp3",
        actual_duration_seconds=10.5,
        target_duration_seconds=10,
        within_tolerance=False,
        voice="en-US-JennyNeural",
    )
    outside = AudioGenOutput(
        file_path="audio.mp3",
        actual_duration_seconds=12,
        target_duration_seconds=10,
        within_tolerance=True,
        voice="en-US-JennyNeural",
    )

    assert inside.within_tolerance is True
    assert outside.within_tolerance is False


def test_audio_input_rejects_directory_path() -> None:
    """O contrato deve exigir um caminho de arquivo."""
    with pytest.raises(ValidationError):
        AudioGenInput(text="hello", output_path=".")


def test_rate_adjustment_moves_toward_target_duration() -> None:
    """Áudios longos devem receber uma taxa de reprodução maior."""
    assert EdgeTTSGenerator._adjust_rate("+0%", 12, 10) == "+20%"


@pytest.mark.asyncio
async def test_generate_retries_with_adjusted_rate(monkeypatch, tmp_path) -> None:
    """Uma duração fora da margem deve disparar uma segunda síntese."""
    generator = EdgeTTSGenerator()
    rates: list[str] = []
    durations = iter((12.0, 10.2))

    async def save_with_retry(text, voice, rate, output_path):
        rates.append(rate)

    monkeypatch.setattr(generator, "_save_with_retry", save_with_retry)
    monkeypatch.setattr(generator, "_duration", lambda _: next(durations))
    monkeypatch.setattr(asyncio, "sleep", lambda _: None)

    result = await generator.generate(
        AudioGenInput(
            text="hello",
            target_duration_seconds=10,
            output_path=str(tmp_path / "audio.mp3"),
        ),
    )

    assert result.within_tolerance is True
    assert rates == ["+0%", "+20%"]
