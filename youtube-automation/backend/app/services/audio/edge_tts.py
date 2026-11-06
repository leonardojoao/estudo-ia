"""Implementação de síntese usando edge-tts."""

import asyncio
import re
from pathlib import Path

import edge_tts
import httpx
from mutagen.mp3 import MP3

from app.core.exceptions import AudioGenerationError

from .base import AudioGenerator
from .schemas import AudioGenInput, AudioGenOutput

VOICES = [
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "en-US-AriaNeural",
    "en-US-DavisNeural",
    "en-GB-SoniaNeural",
    "en-GB-RyanNeural",
]


class EdgeTTSGenerator(AudioGenerator):
    """Gera narração com retry, timeout e ajuste de duração."""

    async def _save_with_retry(
        self,
        text: str,
        voice: str,
        rate: str,
        output_path: str,
    ) -> None:
        """Salva o áudio com três tentativas e backoff exponencial."""
        last_error: Exception | None = None
        for attempt, delay in enumerate((2, 4, 8), start=1):
            try:
                communicator = edge_tts.Communicate(text, voice, rate=rate)
                await asyncio.wait_for(communicator.save(output_path), timeout=30)
                return
            except (
                asyncio.TimeoutError,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
            ) as exc:
                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code != 429
                ):
                    raise AudioGenerationError(
                        "Falha definitiva ao acessar o serviço de voz"
                    ) from exc
                last_error = exc
                if attempt < 3:
                    await asyncio.sleep(delay)
        raise AudioGenerationError(
            "Não foi possível gerar o áudio após três tentativas"
        ) from last_error

    @staticmethod
    def _duration(path: str) -> float:
        """Lê a duração real do MP3 gerado."""
        try:
            duration = float(MP3(path).info.length)
        except (OSError, ValueError, AttributeError) as exc:
            raise AudioGenerationError(
                "O arquivo de áudio foi gerado, mas sua duração não pôde ser lida"
            ) from exc
        if duration <= 0:
            raise AudioGenerationError("O arquivo de áudio possui duração inválida")
        return duration

    @staticmethod
    def _adjust_rate(rate: str, actual: float, target: float) -> str:
        """Ajusta a velocidade para aproximar a duração alvo."""
        match = re.fullmatch(r"([+-]?\d+)%", rate.strip())
        current = int(match.group(1)) if match else 0
        adjustment = round((actual / target - 1) * 100)
        return f"{max(-50, min(100, current + adjustment)):+d}%"

    async def generate(self, input: AudioGenInput) -> AudioGenOutput:
        """Gera o áudio e faz uma segunda síntese quando necessário."""
        output = Path(input.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        rate = input.rate
        for attempt in range(2):
            await self._save_with_retry(input.text, input.voice, rate, str(output))
            actual = self._duration(str(output))
            result = AudioGenOutput(
                file_path=str(output),
                actual_duration_seconds=actual,
                target_duration_seconds=input.target_duration_seconds,
                within_tolerance=True,
                voice=input.voice,
            )
            if (
                input.target_duration_seconds is None
                or result.within_tolerance
                or attempt == 1
            ):
                return result
            rate = self._adjust_rate(
                rate,
                actual,
                input.target_duration_seconds,
            )
        raise AudioGenerationError("Não foi possível concluir a geração do áudio")

    async def list_voices(self) -> list[str]:
        """Retorna as vozes principais suportadas em inglês."""
        return VOICES.copy()
