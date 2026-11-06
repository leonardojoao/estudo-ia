"""Interface dos provedores de geração de texto."""

from abc import ABC, abstractmethod

from .schemas import TextGenInput, TextGenOutput


class TextGenerator(ABC):
    """Contrato substituível para provedores de texto."""

    @abstractmethod
    async def generate(self, input: TextGenInput) -> TextGenOutput:
        """Gera um texto a partir da entrada fornecida."""
        raise NotImplementedError

    @abstractmethod
    async def generate_batch(
        self,
        input: TextGenInput,
        count: int,
    ) -> list[TextGenOutput]:
        """Gera múltiplos textos sequencialmente."""
        raise NotImplementedError
