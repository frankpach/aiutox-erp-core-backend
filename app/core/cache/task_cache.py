"""Task cache service using Redis."""

import json
from typing import Any
from uuid import UUID

from app.core.redis import get_redis_client


class TaskCache:
    """Cache para tareas usando Redis."""

    def __init__(self):
        """Inicializa el cache con cliente Redis."""
        self.redis = get_redis_client()
        self.default_ttl = 300  # 5 minutos

    async def get_user_tasks(
        self, user_id: UUID, filters: dict | None = None
    ) -> list[dict] | None:
        """Obtiene tareas cacheadas de usuario."""
        filters = filters or {}
        cache_key = f"tasks:user:{user_id}:{hash(json.dumps(filters, sort_keys=True))}"

        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            # Si falla el cache, retornar None para que se obtenga de DB
            pass

        return None

    async def set_user_tasks(
        self, user_id: UUID, filters: dict | None = None, tasks: list[Any] = None
    ):
        """Cachea tareas de usuario."""
        if tasks is None:
            return

        filters = filters or {}
        cache_key = f"tasks:user:{user_id}:{hash(json.dumps(filters, sort_keys=True))}"

        try:
            # Serializar tareas
            tasks_data = [self._serialize_task(task) for task in tasks]

            await self.redis.setex(
                cache_key, self.default_ttl, json.dumps(tasks_data)
            )
        except Exception:
            # Si falla el cache, continuar sin error
            pass

    async def invalidate_user_tasks(self, user_id: UUID):
        """Invalida cache de tareas de usuario."""
        pattern = f"tasks:user:{user_id}:*"

        try:
            keys = await self.redis.keys(pattern)

            if keys:
                await self.redis.delete(*keys)
        except Exception:
            # Si falla la invalidación, continuar sin error
            pass

    async def get_task(self, task_id: UUID, tenant_id: UUID) -> dict | None:
        """Obtiene una tarea específica del cache."""
        cache_key = f"task:{tenant_id}:{task_id}"

        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        return None

    async def set_task(self, task: Any, tenant_id: UUID):
        """Cachea una tarea específica."""
        if not task:
            return

        cache_key = f"task:{tenant_id}:{task.id}"

        try:
            task_data = self._serialize_task(task)
            await self.redis.setex(cache_key, self.default_ttl, json.dumps(task_data))
        except Exception:
            pass

    async def invalidate_task(self, task_id: UUID, tenant_id: UUID):
        """Invalida cache de una tarea específica."""
        cache_key = f"task:{tenant_id}:{task_id}"

        try:
            await self.redis.delete(cache_key)
        except Exception:
            pass

    async def get_task_stats(self, tenant_id: UUID, user_id: UUID) -> dict | None:
        """Obtiene estadísticas cacheadas de tareas."""
        cache_key = f"task_stats:{tenant_id}:{user_id}"

        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        return None

    async def set_task_stats(self, tenant_id: UUID, user_id: UUID, stats: dict):
        """Cachea estadísticas de tareas."""
        cache_key = f"task_stats:{tenant_id}:{user_id}"

        try:
            # Stats se cachean por más tiempo (15 minutos)
            await self.redis.setex(cache_key, 900, json.dumps(stats))
        except Exception:
            pass

    async def invalidate_task_stats(self, tenant_id: UUID, user_id: UUID | None = None):
        """Invalida cache de estadísticas."""
        if user_id:
            cache_key = f"task_stats:{tenant_id}:{user_id}"
            try:
                await self.redis.delete(cache_key)
            except Exception:
                pass
        else:
            # Invalidar todas las stats del tenant
            pattern = f"task_stats:{tenant_id}:*"
            try:
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
            except Exception:
                pass

    def _serialize_task(self, task: Any) -> dict:
        """Serializa una tarea para cache."""
        # Si es un modelo SQLAlchemy
        if hasattr(task, "__dict__"):
            task_dict = {}
            for key in task.__dict__:
                if not key.startswith("_"):
                    value = getattr(task, key)
                    # Convertir UUID a string
                    if isinstance(value, UUID):
                        task_dict[key] = str(value)
                    # Convertir datetime a ISO string
                    elif hasattr(value, "isoformat"):
                        task_dict[key] = value.isoformat()
                    # Valores serializables directamente
                    elif isinstance(value, (str, int, float, bool, type(None))):
                        task_dict[key] = value
                    # Listas y dicts
                    elif isinstance(value, (list, dict)):
                        task_dict[key] = value
            return task_dict
        # Si ya es un dict
        elif isinstance(task, dict):
            return task
        # Si tiene método to_dict
        elif hasattr(task, "to_dict"):
            return task.to_dict()
        # Fallback
        else:
            return {}


# Singleton
_task_cache = None


def get_task_cache() -> TaskCache:
    """Obtiene instancia singleton del cache."""
    global _task_cache
    if _task_cache is None:
        _task_cache = TaskCache()
    return _task_cache
