"""Testes do barramento de eventos de jobs."""

import asyncio

import pytest

from app.core.events import EVENT_QUEUE_MAX_SIZE, EventBus


async def _start_subscriber(bus, job_id):
    """Registra subscriber sem bloquear a tarefa de consumo."""
    generator = bus.subscribe(job_id)
    pending = asyncio.create_task(generator.__anext__())
    await asyncio.sleep(0)
    return generator, pending


@pytest.mark.asyncio
async def test_publish_fans_out_to_job_subscribers():
    """Todos os subscribers do mesmo job recebem uma cópia."""
    bus = EventBus()
    first, first_pending = await _start_subscriber(bus, 1)
    second, second_pending = await _start_subscriber(bus, 1)

    await bus.publish(
        1,
        {
            "status": "running",
            "current_step": "video_cutting",
            "progress": 45,
            "step_log": "Cortando",
        },
    )

    first_event, second_event = await asyncio.gather(
        first_pending,
        second_pending,
    )
    assert (
        first_event
        == second_event
        == {
            "job_id": 1,
            "status": "running",
            "current_step": "video_cutting",
            "progress": 45,
            "step_log": "Cortando",
        }
    )
    await first.aclose()
    await second.aclose()


@pytest.mark.asyncio
async def test_global_subscriber_receives_all_jobs_but_job_filter_does_not():
    """Subscriber global recebe tudo; subscriber específico recebe seu job."""
    bus = EventBus()
    global_events, global_pending = await _start_subscriber(bus, None)
    job_events, job_pending = await _start_subscriber(bus, 2)

    await bus.publish(1, {"status": "running"})
    await bus.publish(2, {"status": "completed", "progress": 100})

    assert (await global_pending)["job_id"] == 1
    assert (await global_events.__anext__())["job_id"] == 2
    assert (await job_pending)["job_id"] == 2
    await global_events.aclose()
    await job_events.aclose()


@pytest.mark.asyncio
async def test_slow_subscriber_discards_oldest_event():
    """Overflow preserva os 100 eventos mais recentes."""
    bus = EventBus()
    events, pending = await _start_subscriber(bus, 1)
    await bus.publish(1, {"progress": 0})
    await pending

    for progress in range(EVENT_QUEUE_MAX_SIZE + 1):
        await bus.publish(1, {"progress": progress})

    received = [await events.__anext__() for _ in range(EVENT_QUEUE_MAX_SIZE)]
    assert received[0]["progress"] == 1
    assert received[-1]["progress"] == EVENT_QUEUE_MAX_SIZE
    await events.aclose()


@pytest.mark.asyncio
async def test_subscriber_unsubscribe_cleans_registry():
    """Fechar o generator remove a fila do registry."""
    bus = EventBus()
    events, pending = await _start_subscriber(bus, 7)
    await bus.publish(7, {})
    await pending
    queue = next(iter(bus._subscribers[7]))
    await bus.publish(7, {})

    await events.aclose()

    assert 7 not in bus._subscribers
    assert queue.empty()


@pytest.mark.asyncio
async def test_invalid_job_id_is_rejected():
    """IDs inválidos não podem criar ou publicar eventos."""
    bus = EventBus()
    with pytest.raises(ValueError):
        await bus.publish(0, {})
    with pytest.raises(ValueError):
        await bus.subscribe(-1).__anext__()
