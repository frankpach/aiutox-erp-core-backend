"""
Sistema Pub/Sub con Redis para comunicación entre módulos.

Este módulo implementa un EventBus basado en Redis Pub/Sub que permite
la comunicación asíncrona entre diferentes módulos del sistema.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisEventBus:
    """
    Sistema pub/sub con Redis para comunicación entre módulos.

    Ventajas vs In-Memory:
    - Persistencia de eventos
    - Multi-proceso seguro
    - Escalable horizontalmente
    - Ya configurado en el entorno
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Inicializa el EventBus con conexión a Redis.

        Args:
            redis_url: URL de conexión a Redis
        """
        self.redis_url = redis_url
        self.redis: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None
        self.subscribers: dict[str, list[Callable]] = {}
        self._running = False

    async def connect(self):
        """Establece conexión con Redis."""
        if self.redis is None:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Connected to Redis at {self.redis_url}")

    async def publish(self, topic: str, payload: dict[str, any]) -> None:
        """
        Publica un evento en Redis.

        Args:
            topic: Nombre del topic (ej: "tasks.created")
            payload: Datos del evento
        """
        await self.connect()

        event = {
            "topic": topic,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Publicar en Redis con prefijo
        channel = f"aiutox:{topic}"
        await self.redis.publish(channel, json.dumps(event))
        logger.info(f"Published event to topic '{topic}'")

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """
        Suscribe un handler a un topic.

        Args:
            topic: Nombre del topic
            handler: Función async que recibe el payload
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []

        self.subscribers[topic].append(handler)
        logger.info(f"Subscribed handler to topic '{topic}'")

    async def unsubscribe(self, topic: str, handler: Callable) -> None:
        """
        Desuscribe un handler de un topic.

        Args:
            topic: Nombre del topic
            handler: Función a desuscribir
        """
        if topic in self.subscribers:
            self.subscribers[topic] = [
                h for h in self.subscribers[topic] if h != handler
            ]
            logger.info(f"Unsubscribed handler from topic '{topic}'")

    async def start_subscriber(self):
        """
        Inicia el subscriber que escucha eventos de Redis.

        Este método debe ejecutarse en un task separado para escuchar
        continuamente los eventos publicados.
        """
        if self._running:
            logger.warning("Subscriber already running")
            return

        await self.connect()

        self._running = True
        self.pubsub = self.redis.pubsub()

        # Suscribirse a todos los topics con patrón
        await self.pubsub.psubscribe("aiutox:*")
        logger.info("Started Redis subscriber")

        try:
            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        event = json.loads(message["data"])
                        topic = event["topic"]

                        # Ejecutar handlers suscritos
                        handlers = self.subscribers.get(topic, [])
                        for handler in handlers:
                            try:
                                if asyncio.iscoroutinefunction(handler):
                                    await handler(topic, event["payload"])
                                else:
                                    handler(topic, event["payload"])
                            except Exception as e:
                                logger.error(
                                    f"Error in handler for topic '{topic}': {e}",
                                    exc_info=True,
                                )

                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding event: {e}")
                    except Exception as e:
                        logger.error(f"Error processing event: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in subscriber loop: {e}", exc_info=True)
        finally:
            self._running = False

    async def stop_subscriber(self):
        """
        Detiene el subscriber y cierra conexiones.
        """
        self._running = False

        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.aclose()

        if self.redis:
            await self.redis.aclose()

        logger.info("Stopped Redis subscriber")

    def is_running(self) -> bool:
        """Verifica si el subscriber está activo."""
        return self._running


# Singleton global
_redis_event_bus: RedisEventBus | None = None


async def get_redis_event_bus() -> RedisEventBus:
    """
    Obtiene la instancia global del RedisEventBus.

    Returns:
        Instancia singleton del RedisEventBus
    """
    global _redis_event_bus
    if _redis_event_bus is None:
        from app.core.config_file import get_settings

        settings = get_settings()
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        _redis_event_bus = RedisEventBus(redis_url=redis_url)
    return _redis_event_bus
