"""Task cache service for Redis caching of task operations."""

import json
from typing import Any
from uuid import UUID

import redis.asyncio as redis

from app.core.config import get_settings
from app.schemas.task import TaskResponse


class TaskCacheService:
    """Service for caching task operations using Redis."""

    def __init__(self):
        """Initialize cache service with Redis connection."""
        self.settings = get_settings()
        self.redis_client: redis.Redis | None = None
        self.default_ttl = 300  # 5 minutes

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self.redis_client and self.settings.REDIS_URL:
            self.redis_client = redis.from_url(
                self.settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()

    async def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.redis_client:
            await self.connect()

        if self.redis_client:
            try:
                await self.redis_client.ping()
                return True
            except Exception:
                return False
        return False

    def _make_key(self, *parts: str | UUID) -> str:
        """Create a cache key from parts."""
        return ":".join(str(part) for part in parts)

    async def get_visible_tasks(
        self,
        tenant_id: UUID,
        user_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TaskResponse] | None:
        """Get cached visible tasks for a user."""
        if not await self.is_available():
            return None

        # Create cache key
        key_parts = [
            "tasks",
            "visible",
            str(tenant_id),
            str(user_id),
            f"skip:{skip}",
            f"limit:{limit}",
        ]
        if status:
            key_parts.append(f"status:{status}")
        if priority:
            key_parts.append(f"priority:{priority}")

        cache_key = self._make_key(*key_parts)

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                # Parse cached JSON
                tasks_data = json.loads(cached_data)
                return [TaskResponse.model_validate(task) for task in tasks_data]
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Cache get error: {e}")

        return None

    async def set_visible_tasks(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tasks: list[TaskResponse],
        status: str | None = None,
        priority: str | None = None,
        skip: int = 0,
        limit: int = 100,
        ttl: int | None = None,
    ) -> None:
        """Cache visible tasks for a user."""
        if not await self.is_available():
            return

        # Create cache key (same as get_visible_tasks)
        key_parts = [
            "tasks",
            "visible",
            str(tenant_id),
            str(user_id),
            f"skip:{skip}",
            f"limit:{limit}",
        ]
        if status:
            key_parts.append(f"status:{status}")
        if priority:
            key_parts.append(f"priority:{priority}")

        cache_key = self._make_key(*key_parts)

        try:
            # Serialize tasks to JSON
            tasks_data = [task.model_dump() for task in tasks]
            cached_json = json.dumps(tasks_data, default=str)

            # Set cache with TTL
            await self.redis_client.setex(
                cache_key, ttl or self.default_ttl, cached_json
            )
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Cache set error: {e}")

    async def get_agenda(
        self,
        tenant_id: UUID,
        user_id: UUID,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any] | None:
        """Get cached agenda data."""
        if not await self.is_available():
            return None

        key_parts = [
            "tasks",
            "agenda",
            str(tenant_id),
            str(user_id),
        ]
        if start_date:
            key_parts.append(f"start:{start_date}")
        if end_date:
            key_parts.append(f"end:{end_date}")

        cache_key = self._make_key(*key_parts)

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Cache get error: {e}")

        return None

    async def set_agenda(
        self,
        tenant_id: UUID,
        user_id: UUID,
        agenda_data: dict[str, Any],
        start_date: str | None = None,
        end_date: str | None = None,
        ttl: int | None = None,
    ) -> None:
        """Cache agenda data."""
        if not await self.is_available():
            return

        key_parts = [
            "tasks",
            "agenda",
            str(tenant_id),
            str(user_id),
        ]
        if start_date:
            key_parts.append(f"start:{start_date}")
        if end_date:
            key_parts.append(f"end:{end_date}")

        cache_key = self._make_key(*key_parts)

        try:
            cached_json = json.dumps(agenda_data, default=str)
            await self.redis_client.setex(
                cache_key, ttl or self.default_ttl, cached_json
            )
        except Exception as e:
            print(f"Cache set error: {e}")

    async def get_calendar_sources(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any] | None:
        """Get cached calendar sources."""
        if not await self.is_available():
            return None

        cache_key = self._make_key(
            "tasks", "calendar_sources", str(tenant_id), str(user_id)
        )

        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            print(f"Cache get error: {e}")

        return None

    async def set_calendar_sources(
        self,
        tenant_id: UUID,
        user_id: UUID,
        sources_data: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Cache calendar sources."""
        if not await self.is_available():
            return

        cache_key = self._make_key(
            "tasks", "calendar_sources", str(tenant_id), str(user_id)
        )

        try:
            cached_json = json.dumps(sources_data, default=str)
            await self.redis_client.setex(
                cache_key, ttl or 3600, cached_json  # 1 hour for calendar sources
            )
        except Exception as e:
            print(f"Cache set error: {e}")

    async def invalidate_user_cache(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> None:
        """Invalidate all cache entries for a specific user."""
        if not await self.is_available():
            return

        try:
            # Find all keys for this user
            pattern = self._make_key("tasks", "*", str(tenant_id), str(user_id), "*")
            keys = await self.redis_client.keys(pattern)

            if keys:
                await self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache invalidation error: {e}")

    async def invalidate_task_cache(
        self,
        tenant_id: UUID,
        task_id: UUID | None = None,
    ) -> None:
        """Invalidate cache entries related to a task or all tasks in tenant."""
        if not await self.is_available():
            return

        try:
            if task_id:
                # Invalidate specific task cache (if implemented)
                pattern = self._make_key(
                    "tasks", "*", str(tenant_id), "*", f"*{task_id}*"
                )
            else:
                # Invalidate all task cache for tenant
                pattern = self._make_key("tasks", "*", str(tenant_id), "*")

            keys = await self.redis_client.keys(pattern)

            if keys:
                await self.redis_client.delete(*keys)
        except Exception as e:
            print(f"Cache invalidation error: {e}")

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get Redis cache statistics."""
        if not await self.is_available():
            return {"available": False}

        try:
            info = await self.redis_client.info()
            return {
                "available": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", "N/A"),
                "total_commands_processed": info.get("total_commands_processed", "N/A"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}


# Global cache service instance
task_cache_service = TaskCacheService()
