"""Servicio de caché optimizado para tareas con Redis y estrategias avanzadas."""

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config_file import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class TaskCacheOptimized:
    """Servicio de caché optimizado para operaciones de tareas."""

    def __init__(self, redis_url: str | None = None) -> None:
        """Inicializar servicio de caché con Redis."""
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client: Redis | None = None
        self.default_ttl = 300  # 5 minutos
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }

    async def connect(self) -> None:
        """Conectar a Redis."""
        if not self._redis_client:
            try:
                self._redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
                # Test connection
                await self._redis_client.ping()
                logger.info("Conectado a Redis para caché de tareas")
            except Exception as e:
                logger.error(f"Error conectando a Redis: {e}")
                self._redis_client = None

    async def disconnect(self) -> None:
        """Desconectar de Redis."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

    @property
    def redis(self) -> Redis:
        """Obtener cliente Redis con conexión automática."""
        if not self._redis_client:
            raise RuntimeError("Redis no está conectado. Llamar a connect() primero.")
        return self._redis_client

    async def get(self, key: str) -> Any | None:
        """Obtener valor del caché."""
        try:
            value = await self.redis.get(key)
            if value is not None:
                self.stats["hits"] += 1
                # Intentar deserializar JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            logger.error(f"Error obteniendo caché para key {key}: {e}")
            self.stats["misses"] += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        serialize: bool = True,
    ) -> bool:
        """Establecer valor en caché con TTL opcional."""
        try:
            ttl = ttl or self.default_ttl

            # Serializar si es necesario
            if serialize and not isinstance(value, (str, int, float, bool)):
                value = json.dumps(value, default=str)
            elif serialize:
                value = str(value)

            result = await self.redis.setex(key, ttl, value)
            if result:
                self.stats["sets"] += 1
            return bool(result)
        except Exception as e:
            logger.error(f"Error estableciendo caché para key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Eliminar clave del caché."""
        try:
            result = await self.redis.delete(key)
            if result:
                self.stats["deletes"] += 1
            return bool(result)
        except Exception as e:
            logger.error(f"Error eliminando caché para key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Eliminar claves que coincidan con patrón."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                result = await self.redis.delete(*keys)
                self.stats["deletes"] += result
                return result
            return 0
        except Exception as e:
            logger.error(f"Error eliminando patrón {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Verificar si clave existe en caché."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Error verificando existencia de key {key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """Obtener TTL restante de una clave."""
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Error obteniendo TTL para key {key}: {e}")
            return -1

    async def extend_ttl(self, key: str, additional_ttl: int) -> bool:
        """Extender TTL de una clave existente."""
        try:
            current_ttl = await self.get_ttl(key)
            if current_ttl > 0:
                new_ttl = current_ttl + additional_ttl
                return bool(await self.redis.expire(key, new_ttl))
            return False
        except Exception as e:
            logger.error(f"Error extendiendo TTL para key {key}: {e}")
            return False

    # Métodos especializados para caché de tareas
    async def cache_task(self, task_id: UUID, tenant_id: UUID, task_data: dict, ttl: int = 300) -> None:
        """Cachear una tarea individual."""
        key = f"task:{task_id}:{tenant_id}"
        await self.set(key, task_data, ttl)

    async def get_cached_task(self, task_id: UUID, tenant_id: UUID) -> dict | None:
        """Obtener tarea cachéada."""
        key = f"task:{task_id}:{tenant_id}"
        return await self.get(key)

    async def cache_task_list(
        self,
        tenant_id: UUID,
        filters: dict[str, Any],
        tasks: list[dict],
        ttl: int = 120,
    ) -> None:
        """Cachear listado de tareas con filtros."""
        # Crear clave basada en filtros
        filter_parts = []
        for k, v in sorted(filters.items()):
            if v is not None:
                filter_parts.append(f"{k}:{v}")

        filter_hash = hash(tuple(filter_parts))
        key = f"task_list:{tenant_id}:{filter_hash}"

        await self.set(key, tasks, ttl)

    async def get_cached_task_list(
        self,
        tenant_id: UUID,
        filters: dict[str, Any],
    ) -> list[dict] | None:
        """Obtener listado de tareas cachéado."""
        filter_parts = []
        for k, v in sorted(filters.items()):
            if v is not None:
                filter_parts.append(f"{k}:{v}")

        filter_hash = hash(tuple(filter_parts))
        key = f"task_list:{tenant_id}:{filter_hash}"

        result = await self.get(key)
        return result if isinstance(result, list) else None

    async def cache_user_visibility(
        self,
        tenant_id: UUID,
        user_id: UUID,
        group_ids: tuple,
        tasks: list[dict],
        ttl: int = 60,
    ) -> None:
        """Cachear tareas visibles para usuario."""
        groups_str = ",".join(sorted(str(gid) for gid in group_ids)) if group_ids else "none"
        key = f"visible_tasks:{tenant_id}:{user_id}:{groups_str}"

        await self.set(key, tasks, ttl)

    async def get_cached_user_visibility(
        self,
        tenant_id: UUID,
        user_id: UUID,
        group_ids: tuple,
    ) -> list[dict] | None:
        """Obtener tareas visibles cachéadas para usuario."""
        groups_str = ",".join(sorted(str(gid) for gid in group_ids)) if group_ids else "none"
        key = f"visible_tasks:{tenant_id}:{user_id}:{groups_str}"

        result = await self.get(key)
        return result if isinstance(result, list) else None

    async def cache_task_statistics(self, tenant_id: UUID, stats: dict, ttl: int = 600) -> None:
        """Cachear estadísticas de tareas."""
        key = f"task_stats:{tenant_id}"
        await self.set(key, stats, ttl)

    async def get_cached_task_statistics(self, tenant_id: UUID) -> dict | None:
        """Obtener estadísticas cachéadas."""
        key = f"task_stats:{tenant_id}"
        result = await self.get(key)
        return result if isinstance(result, dict) else None

    async def cache_search_results(
        self,
        tenant_id: UUID,
        query_hash: str,
        results: list[dict],
        ttl: int = 180,
    ) -> None:
        """Cachear resultados de búsqueda."""
        key = f"task_search:{tenant_id}:{query_hash}"
        await self.set(key, results, ttl)

    async def get_cached_search_results(
        self,
        tenant_id: UUID,
        query_hash: str,
    ) -> list[dict] | None:
        """Obtener resultados de búsqueda cachéados."""
        key = f"task_search:{tenant_id}:{query_hash}"
        result = await self.get(key)
        return result if isinstance(result, list) else None

    async def invalidate_user_cache(self, tenant_id: UUID, user_id: UUID) -> None:
        """Invalidar todo el caché relacionado con un usuario."""
        patterns = [
            f"visible_tasks:{tenant_id}:{user_id}:*",
            f"task_list:{tenant_id}:*",
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

    async def invalidate_task_cache(self, tenant_id: UUID, task_id: UUID) -> None:
        """Invalidar caché de una tarea específica."""
        keys = [
            f"task:{task_id}:{tenant_id}",
            f"task_list:{tenant_id}:*",
            f"visible_tasks:{tenant_id}:*",
        ]

        for key in keys:
            if "*" in key:
                await self.delete_pattern(key)
            else:
                await self.delete(key)

    async def invalidate_tenant_cache(self, tenant_id: UUID) -> None:
        """Invalidar todo el caché de un tenant."""
        patterns = [
            f"task:{tenant_id}:*",
            f"task_list:{tenant_id}:*",
            f"visible_tasks:{tenant_id}:*",
            f"task_stats:{tenant_id}",
            f"task_search:{tenant_id}:*",
        ]

        for pattern in patterns:
            await self.delete_pattern(pattern)

    # Métodos de mantenimiento y estadísticas
    async def get_stats(self) -> dict[str, Any]:
        """Obtener estadísticas del caché."""
        try:
            redis_info = await self.redis.info()
            return {
                **self.stats,
                "redis_memory_used": redis_info.get("used_memory_human", "N/A"),
                "redis_connected_clients": redis_info.get("connected_clients", 0),
                "redis_keyspace_hits": redis_info.get("keyspace_hits", 0),
                "redis_keyspace_misses": redis_info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(),
            }
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de Redis: {e}")
            return {
                **self.stats,
                "hit_rate": self._calculate_hit_rate(),
                "redis_error": str(e),
            }

    def _calculate_hit_rate(self) -> float:
        """Calcular tasa de hits."""
        total = self.stats["hits"] + self.stats["misses"]
        if total == 0:
            return 0.0
        return (self.stats["hits"] / total) * 100

    async def cleanup_expired_keys(self, max_keys: int = 1000) -> int:
        """Limpiar claves expiradas (mantenimiento)."""
        try:
            # Obtener claves con TTL cercano a expiración
            cursor = 0
            cleaned = 0

            while cursor != 0 and cleaned < max_keys:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match="task:*",
                    count=100,
                )

                for key in keys:
                    ttl = await self.get_ttl(key)
                    if ttl == -1:  # Sin TTL, establecer TTL por defecto
                        await self.redis.expire(key, self.default_ttl)
                    elif ttl == -2:  # Expirada
                        await self.delete(key)
                        cleaned += 1

            return cleaned
        except Exception as e:
            logger.error(f"Error en limpieza de caché: {e}")
            return 0

    async def warm_up_cache(self, tenant_id: UUID, popular_tasks: list[dict]) -> None:
        """Precargar caché con tareas populares."""
        for task in popular_tasks:
            task_id = task.get("id")
            if task_id:
                await self.cache_task(
                    UUID(task_id),
                    tenant_id,
                    task,
                    ttl=600,  # 10 minutos para warm-up
                )

    async def health_check(self) -> dict[str, Any]:
        """Verificar salud del servicio de caché."""
        try:
            start_time = datetime.now(UTC)
            await self.redis.ping()
            latency = (datetime.now(UTC) - start_time).total_seconds() * 1000

            return {
                "status": "healthy",
                "latency_ms": latency,
                "connected": True,
                "stats": await self.get_stats(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False,
                "stats": self.stats,
            }


# Instancia global del caché
_task_cache_instance: TaskCacheOptimized | None = None


async def get_task_cache_optimized() -> TaskCacheOptimized:
    """Obtener instancia global del caché optimizado."""
    global _task_cache_instance

    if _task_cache_instance is None:
        _task_cache_instance = TaskCacheOptimized()
        await _task_cache_instance.connect()

    return _task_cache_instance


async def close_task_cache_optimized() -> None:
    """Cerrar instancia global del caché."""
    global _task_cache_instance

    if _task_cache_instance:
        await _task_cache_instance.disconnect()
        _task_cache_instance = None
