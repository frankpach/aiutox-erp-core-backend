"""
Servicio de caching para vistas de calendario usando Redis.

Implementa estrategias de cache para optimizar el rendimiento de las vistas
de calendario y board de tareas.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CalendarCache:
    """
    Servicio de caching para vistas de calendario usando Redis.

    Estrategia de cache:
    - calendar:view:{tenant_id}:{view_type}:{date} -> 5 min TTL
    - task:board:{tenant_id} -> 1 min TTL (más dinámico)
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/1"):
        """
        Inicializa el servicio de cache.

        Args:
            redis_url: URL de conexión a Redis (usa DB 1 para cache)
        """
        self.redis_url = redis_url
        self.redis: redis.Redis | None = None
        self.default_ttl = 300  # 5 minutos

    async def connect(self):
        """Establece conexión con Redis."""
        if self.redis is None:
            self.redis = await redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Calendar cache connected to Redis at {self.redis_url}")

    async def get_calendar_view(
        self, tenant_id: UUID, view_type: str, date: datetime
    ) -> dict[str, Any] | None:
        """
        Obtiene vista de calendario cacheada.

        Args:
            tenant_id: ID del tenant
            view_type: Tipo de vista (month, week, day, agenda)
            date: Fecha de la vista

        Returns:
            Datos cacheados o None si no existe
        """
        await self.connect()

        cache_key = f"calendar:view:{tenant_id}:{view_type}:{date.strftime('%Y-%m-%d')}"
        cached = await self.redis.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return json.loads(cached)

        logger.debug(f"Cache miss for {cache_key}")
        return None

    async def set_calendar_view(
        self,
        tenant_id: UUID,
        view_type: str,
        date: datetime,
        data: dict[str, Any],
        ttl: int | None = None,
    ):
        """
        Guarda vista de calendario en cache.

        Args:
            tenant_id: ID del tenant
            view_type: Tipo de vista
            date: Fecha de la vista
            data: Datos a cachear
            ttl: Tiempo de vida en segundos (default: 5 min)
        """
        await self.connect()

        cache_key = f"calendar:view:{tenant_id}:{view_type}:{date.strftime('%Y-%m-%d')}"
        ttl = ttl or self.default_ttl

        await self.redis.setex(cache_key, ttl, json.dumps(data, default=str))
        logger.debug(f"Cached {cache_key} with TTL {ttl}s")

    async def invalidate_calendar_views(self, tenant_id: UUID):
        """
        Invalida todas las vistas de calendario de un tenant.

        Args:
            tenant_id: ID del tenant
        """
        await self.connect()

        pattern = f"calendar:view:{tenant_id}:*"
        keys = []

        # Usar scan para evitar bloquear Redis con KEYS
        async for key in self.redis.scan_iter(match=pattern):
            keys.append(key)

        if keys:
            await self.redis.delete(*keys)
            logger.info(
                f"Invalidated {len(keys)} calendar view caches for tenant {tenant_id}"
            )

    async def get_board_view(self, tenant_id: UUID) -> list[dict[str, Any]] | None:
        """
        Obtiene vista Board cacheada.

        Args:
            tenant_id: ID del tenant

        Returns:
            Datos cacheados o None si no existe
        """
        await self.connect()

        cache_key = f"task:board:{tenant_id}"
        cached = await self.redis.get(cache_key)

        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return json.loads(cached)

        logger.debug(f"Cache miss for {cache_key}")
        return None

    async def set_board_view(
        self,
        tenant_id: UUID,
        data: list[dict[str, Any]],
        ttl: int = 60,  # 1 minuto para Board (más dinámico)
    ):
        """
        Guarda vista Board en cache.

        Args:
            tenant_id: ID del tenant
            data: Datos a cachear
            ttl: Tiempo de vida en segundos (default: 1 min)
        """
        await self.connect()

        cache_key = f"task:board:{tenant_id}"

        await self.redis.setex(cache_key, ttl, json.dumps(data, default=str))
        logger.debug(f"Cached {cache_key} with TTL {ttl}s")

    async def invalidate_board_view(self, tenant_id: UUID):
        """
        Invalida la vista Board de un tenant.

        Args:
            tenant_id: ID del tenant
        """
        await self.connect()

        cache_key = f"task:board:{tenant_id}"
        await self.redis.delete(cache_key)
        logger.debug(f"Invalidated board view cache for tenant {tenant_id}")

    async def close(self):
        """Cierra la conexión con Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Calendar cache connection closed")


# Singleton global
_calendar_cache: CalendarCache | None = None


async def get_calendar_cache() -> CalendarCache:
    """
    Obtiene la instancia global del CalendarCache.

    Returns:
        Instancia singleton del CalendarCache
    """
    global _calendar_cache
    if _calendar_cache is None:
        from app.core.config import get_settings

        settings = get_settings()
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/1")
        _calendar_cache = CalendarCache(redis_url=redis_url)
    return _calendar_cache
