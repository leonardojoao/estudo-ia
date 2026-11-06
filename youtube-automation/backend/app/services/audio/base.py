"""Interface dos provedores de síntese de voz."""

from abc import ABC, abstractmethod

from .schemas import AudioGenInput, AudioGenOutput


class AudioGenerator(ABC):
    """Contrato substituível para provedores de áudio."""

    @abstractmethod
    async def generate(self, input: AudioGenInput) -> AudioGenOutput:
        """Gera um arquivo de áudio."""
        raise NotImplementedError

    @abstractmethod
    async def list_voices(self) -> list[str]:
        """Lista vozes disponíveis."""
        raise NotImplementedError
