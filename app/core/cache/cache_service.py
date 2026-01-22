"""Cache service for user roles and permissions using Redis."""

import json
from uuid import UUID

from app.core.config_file import get_settings

settings = get_settings()


class CacheService:
    """Service for caching user roles and permissions in Redis."""

    def __init__(self):
        """Initialize cache service."""
        self.redis = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            import redis
            self.redis = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
            )
        except Exception:
            # Redis not available, cache will be disabled
            pass

    def get_user_roles(self, user_id: UUID) -> list[str] | None:
        """Get user roles from cache."""
        if not self.redis:
            return None

        try:
            key = f"user:{user_id}:roles"
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    def set_user_roles(self, user_id: UUID, roles: list[str]) -> None:
        """Set user roles in cache."""
        if not self.redis:
            return

        try:
            key = f"user:{user_id}:roles"
            self.redis.setex(key, 300, json.dumps(roles))  # 5 minutes TTL
        except Exception:
            pass

    def get_user_permissions(self, user_id: UUID) -> list[str] | None:
        """Get user permissions from cache."""
        if not self.redis:
            return None

        try:
            key = f"user:{user_id}:permissions"
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass
        return None

    def set_user_permissions(self, user_id: UUID, permissions: list[str]) -> None:
        """Set user permissions in cache."""
        if not self.redis:
            return

        try:
            key = f"user:{user_id}:permissions"
            self.redis.setex(key, 300, json.dumps(permissions))  # 5 minutes TTL
        except Exception:
            pass

    def invalidate_user_cache(self, user_id: UUID) -> None:
        """Invalidate all cache entries for a user."""
        if not self.redis:
            return

        try:
            keys = [f"user:{user_id}:roles", f"user:{user_id}:permissions"]
            self.redis.delete(*keys)
        except Exception:
            pass


# Global cache service instance
cache_service = CacheService()
