"""SSE connection manager for real-time notifications."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class SSEConnectionManager:
    """Gestor de conexiones SSE por usuario."""

    def __init__(self):
        """Initialize SSE connection manager."""
        self.connections: dict[UUID, set[asyncio.Queue]] = defaultdict(set)

    async def connect(self, user_id: UUID) -> asyncio.Queue:
        """Conecta un usuario y retorna su cola de mensajes."""
        queue = asyncio.Queue()
        self.connections[user_id].add(queue)
        logger.info(f"SSE connection established for user {user_id}")
        return queue

    def disconnect(self, user_id: UUID, queue: asyncio.Queue) -> None:
        """Desconecta un usuario."""
        if user_id in self.connections:
            self.connections[user_id].discard(queue)
            if not self.connections[user_id]:
                del self.connections[user_id]
        logger.info(f"SSE connection closed for user {user_id}")

    async def send_to_user(
        self, user_id: UUID, event_type: str, data: dict[str, Any]
    ) -> None:
        """Envía evento a todas las conexiones de un usuario."""
        if user_id not in self.connections:
            return

        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        dead_queues = set()
        for queue in self.connections[user_id]:
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"Error sending SSE to user {user_id}: {e}")
                dead_queues.add(queue)

        # Limpiar colas muertas
        for queue in dead_queues:
            self.connections[user_id].discard(queue)

    async def send_to_tenant(
        self, tenant_id: UUID, event_type: str, data: dict[str, Any]
    ) -> None:
        """Envía evento a todos los usuarios de un tenant."""
        # Nota: Requeriría un mapeo de tenant_id a user_ids
        # Por ahora, solo implementamos send_to_user
        pass

    def get_connection_count(self, user_id: UUID) -> int:
        """Obtiene el número de conexiones activas de un usuario."""
        return len(self.connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """Obtiene el número total de conexiones activas."""
        return sum(len(queues) for queues in self.connections.values())


# Global SSE manager instance
_sse_manager = None


def get_sse_manager() -> SSEConnectionManager:
    """Get SSE connection manager instance."""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEConnectionManager()
    return _sse_manager
