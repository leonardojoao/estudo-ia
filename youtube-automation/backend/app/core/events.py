"""Barramento pub/sub em memória para eventos de processamento."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

EVENT_QUEUE_MAX_SIZE = 100
EVENT_FIELDS = (
    "job_id",
    "status",
    "current_step",
    "progress",
    "step_log",
)


class EventBus:
    """Distribui eventos de jobs para subscribers por job ou globais."""

    def __init__(self) -> None:
        self._subscribers: dict[int | None, set[asyncio.Queue[dict[str, Any]]]] = {}

    @staticmethod
    def _normalize_event(job_id: int, event: dict[str, Any]) -> dict[str, Any]:
        """Normaliza o contrato serializável de um evento."""
        if job_id <= 0:
            raise ValueError("job_id deve ser maior que zero")
        return {
            "job_id": job_id,
            "status": str(event.get("status", "")),
            "current_step": str(event.get("current_step", "")),
            "progress": int(event.get("progress", 0)),
            "step_log": str(event.get("step_log", "")),
        }

    async def publish(self, job_id: int, event: dict[str, Any]) -> None:
        """Publica uma cópia do evento para todos os subscribers elegíveis."""
        normalized = self._normalize_event(job_id, event)
        subscribers = set(self._subscribers.get(job_id, set())) | set(
            self._subscribers.get(None, set())
        )
        for queue in subscribers:
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(normalized.copy())

    async def subscribe(
        self,
        job_id: int | None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Registra subscriber e produz eventos até o cancelamento."""
        if job_id is not None and job_id <= 0:
            raise ValueError("job_id deve ser maior que zero")
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=EVENT_QUEUE_MAX_SIZE
        )
        self._subscribers.setdefault(job_id, set()).add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self.unsubscribe(job_id, queue)

    def unsubscribe(
        self,
        job_id: int | None,
        queue: asyncio.Queue[dict[str, Any]],
    ) -> None:
        """Remove uma fila de subscriber de forma idempotente."""
        subscribers = self._subscribers.get(job_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        while not queue.empty():
            queue.get_nowait()
        if not subscribers:
            self._subscribers.pop(job_id, None)


event_bus = EventBus()
