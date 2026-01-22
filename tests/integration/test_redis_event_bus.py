"""
Test de integración para RedisEventBus.

Prueba el sistema pub/sub con Redis para comunicación entre módulos.
"""

import asyncio
from uuid import uuid4

import pytest

from app.core.pubsub import get_redis_event_bus
from app.core.pubsub.payloads import TaskCreatedPayload
from app.core.pubsub.topics import TASK_CREATED, TASK_UPDATED


@pytest.mark.asyncio
async def test_redis_event_bus_publish_subscribe():
    """Test básico de publicación y suscripción."""
    event_bus = await get_redis_event_bus()
    received_events = []

    async def handler(topic: str, payload: dict):
        """Handler de prueba."""
        received_events.append({"topic": topic, "payload": payload})

    # Iniciar el subscriber en background
    subscriber_task = asyncio.create_task(event_bus.start_subscriber())

    # Dar tiempo para que el subscriber se inicie
    await asyncio.sleep(0.2)

    # Suscribirse al topic
    await event_bus.subscribe(TASK_CREATED, handler)

    # Dar tiempo para que la suscripción se establezca
    await asyncio.sleep(0.1)

    # Publicar evento
    test_payload = {
        "task_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "title": "Test Task",
        "status": "todo",
        "priority": "medium",
        "created_by_id": str(uuid4()),
    }

    await event_bus.publish(TASK_CREATED, test_payload)

    # Dar tiempo para que el evento se procese
    await asyncio.sleep(0.5)

    # Verificar que se recibió el evento
    assert len(received_events) == 1
    assert received_events[0]["topic"] == TASK_CREATED
    assert received_events[0]["payload"]["task_id"] == test_payload["task_id"]
    assert received_events[0]["payload"]["title"] == test_payload["title"]

    # Cleanup
    await event_bus.unsubscribe(TASK_CREATED, handler)
    await event_bus.stop_subscriber()
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_redis_event_bus_multiple_subscribers():
    """Test con múltiples suscriptores al mismo topic."""
    event_bus = await get_redis_event_bus()
    received_events_1 = []
    received_events_2 = []

    async def handler_1(topic: str, payload: dict):
        received_events_1.append({"topic": topic, "payload": payload})

    async def handler_2(topic: str, payload: dict):
        received_events_2.append({"topic": topic, "payload": payload})

    # Iniciar el subscriber en background
    subscriber_task = asyncio.create_task(event_bus.start_subscriber())

    # Dar tiempo para que el subscriber se inicie
    await asyncio.sleep(0.2)

    # Suscribir ambos handlers
    await event_bus.subscribe(TASK_UPDATED, handler_1)
    await event_bus.subscribe(TASK_UPDATED, handler_2)

    await asyncio.sleep(0.1)

    # Publicar evento
    test_payload = {
        "task_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "title": "Updated Task",
        "status": "in_progress",
        "priority": "high",
        "updated_by_id": str(uuid4()),
    }

    await event_bus.publish(TASK_UPDATED, test_payload)

    await asyncio.sleep(0.5)

    # Verificar que ambos handlers recibieron el evento
    assert len(received_events_1) == 1
    assert len(received_events_2) == 1
    assert received_events_1[0]["payload"]["task_id"] == test_payload["task_id"]
    assert received_events_2[0]["payload"]["task_id"] == test_payload["task_id"]

    # Cleanup
    await event_bus.unsubscribe(TASK_UPDATED, handler_1)
    await event_bus.unsubscribe(TASK_UPDATED, handler_2)
    await event_bus.stop_subscriber()
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_redis_event_bus_unsubscribe():
    """Test de desuscripción de eventos."""
    event_bus = await get_redis_event_bus()
    received_events = []

    async def handler(topic: str, payload: dict):
        received_events.append({"topic": topic, "payload": payload})

    # Iniciar el subscriber en background
    subscriber_task = asyncio.create_task(event_bus.start_subscriber())

    # Dar tiempo para que el subscriber se inicie
    await asyncio.sleep(0.2)

    # Suscribirse
    await event_bus.subscribe(TASK_CREATED, handler)
    await asyncio.sleep(0.1)

    # Publicar primer evento
    test_payload_1 = {
        "task_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "title": "Task 1",
        "status": "todo",
        "priority": "low",
        "created_by_id": str(uuid4()),
    }
    await event_bus.publish(TASK_CREATED, test_payload_1)
    await asyncio.sleep(0.3)

    # Desuscribirse
    await event_bus.unsubscribe(TASK_CREATED, handler)
    await asyncio.sleep(0.1)

    # Publicar segundo evento (no debería recibirse)
    test_payload_2 = {
        "task_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "title": "Task 2",
        "status": "todo",
        "priority": "medium",
        "created_by_id": str(uuid4()),
    }
    await event_bus.publish(TASK_CREATED, test_payload_2)
    await asyncio.sleep(0.3)

    # Verificar que solo se recibió el primer evento
    assert len(received_events) == 1
    assert received_events[0]["payload"]["title"] == "Task 1"

    # Cleanup
    await event_bus.stop_subscriber()
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_redis_event_bus_payload_validation():
    """Test de validación de payloads con Pydantic."""
    event_bus = await get_redis_event_bus()
    received_events = []

    async def handler(topic: str, payload: dict):
        # Validar con Pydantic
        validated = TaskCreatedPayload(**payload)
        received_events.append(validated)

    # Iniciar el subscriber en background
    subscriber_task = asyncio.create_task(event_bus.start_subscriber())

    # Dar tiempo para que el subscriber se inicie
    await asyncio.sleep(0.2)

    # Suscribirse
    await event_bus.subscribe(TASK_CREATED, handler)
    await asyncio.sleep(0.1)

    # Publicar evento válido
    valid_payload = {
        "task_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "event_type": "task.created",
        "title": "Valid Task",
        "status": "todo",
        "priority": "medium",
        "created_by_id": str(uuid4()),
    }

    await event_bus.publish(TASK_CREATED, valid_payload)
    await asyncio.sleep(0.5)

    # Verificar que se validó correctamente
    assert len(received_events) == 1
    assert isinstance(received_events[0], TaskCreatedPayload)
    assert received_events[0].title == "Valid Task"
    assert received_events[0].status == "todo"

    # Cleanup
    await event_bus.unsubscribe(TASK_CREATED, handler)
    await event_bus.stop_subscriber()
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_redis_event_bus_concurrent_events():
    """Test de manejo de eventos concurrentes."""
    event_bus = await get_redis_event_bus()
    received_events = []
    lock = asyncio.Lock()

    async def handler(topic: str, payload: dict):
        async with lock:
            received_events.append({"topic": topic, "payload": payload})

    # Iniciar el subscriber en background
    subscriber_task = asyncio.create_task(event_bus.start_subscriber())

    # Dar tiempo para que el subscriber se inicie
    await asyncio.sleep(0.2)

    await event_bus.subscribe(TASK_CREATED, handler)
    await asyncio.sleep(0.1)

    # Publicar múltiples eventos concurrentemente
    tasks = []
    for i in range(5):
        payload = {
            "task_id": str(uuid4()),
            "tenant_id": str(uuid4()),
            "title": f"Task {i}",
            "status": "todo",
            "priority": "medium",
            "created_by_id": str(uuid4()),
        }
        tasks.append(event_bus.publish(TASK_CREATED, payload))

    await asyncio.gather(*tasks)
    await asyncio.sleep(1.0)

    # Verificar que se recibieron todos los eventos
    assert len(received_events) == 5
    titles = {event["payload"]["title"] for event in received_events}
    assert titles == {f"Task {i}" for i in range(5)}

    # Cleanup
    await event_bus.unsubscribe(TASK_CREATED, handler)
    await event_bus.stop_subscriber()
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
