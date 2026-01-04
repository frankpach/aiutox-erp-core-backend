"""Redis cache implementation for configuration module.

This module provides optional caching layer for configuration values
to reduce database queries and improve performance.

Cache Strategy:
- Cache key pattern: "config:{tenant_id}:{module}:{key}"
- TTL: 300 seconds (5 minutes) by default
- Invalidation: On update/delete operations
"""

import json
import logging
from typing import Any
from uuid import UUID

import redis
from redis.exceptions import ConnectionError, RedisError

from app.core.config_file import Settings

logger = logging.getLogger(__name__)


class ConfigCache:
    """Redis cache for configuration values."""

    def __init__(self, enabled: bool = True, ttl: int = 300):
        """Initialize config cache.

        Args:
            enabled: Whether caching is enabled (default: True)
            ttl: Time-to-live for cached values in seconds (default: 300 = 5 minutes)
        """
        self.enabled = enabled
        self.ttl = ttl
        self._redis_client: redis.Redis | None = None
        self._connection_attempted = False

        if self.enabled:
            self._initialize_redis()

    def _initialize_redis(self) -> None:
        """Initialize Redis connection."""
        if self._connection_attempted:
            return

        self._connection_attempted = True
        try:
            settings = Settings()
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self._redis_client.ping()
            logger.info("Config cache: Redis connected successfully")
        except (ConnectionError, RedisError) as e:
            logger.warning(
                f"Config cache: Failed to connect to Redis: {e}. "
                "Caching is disabled. Config will work without cache."
            )
            self._redis_client = None
            self.enabled = False

    def _make_key(self, tenant_id: UUID, module: str, key: str) -> str:
        """Generate cache key.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key

        Returns:
            Cache key string
        """
        return f"config:{tenant_id}:{module}:{key}"

    def _make_module_pattern(self, tenant_id: UUID, module: str) -> str:
        """Generate cache key pattern for a module.

        Args:
            tenant_id: Tenant ID
            module: Module name

        Returns:
            Cache key pattern for scanning
        """
        return f"config:{tenant_id}:{module}:*"

    def get(self, tenant_id: UUID, module: str, key: str) -> Any | None:
        """Get a cached configuration value.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key

        Returns:
            Cached value or None if not found/cache disabled
        """
        if not self.enabled or not self._redis_client:
            return None

        try:
            cache_key = self._make_key(tenant_id, module, key)
            cached_value = self._redis_client.get(cache_key)

            if cached_value is not None:
                # Deserialize JSON
                return json.loads(cached_value)

            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Config cache: Failed to get value: {e}")
            return None

    def set(
        self, tenant_id: UUID, module: str, key: str, value: Any, ttl: int | None = None
    ) -> bool:
        """Set a configuration value in cache.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key
            value: Value to cache
            ttl: Custom TTL in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self.enabled or not self._redis_client:
            return False

        try:
            cache_key = self._make_key(tenant_id, module, key)
            # Serialize to JSON
            serialized_value = json.dumps(value)

            # Set with TTL
            self._redis_client.setex(cache_key, ttl or self.ttl, serialized_value)
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.warning(f"Config cache: Failed to set value: {e}")
            return False

    def delete(self, tenant_id: UUID, module: str, key: str) -> bool:
        """Delete a cached configuration value.

        Args:
            tenant_id: Tenant ID
            module: Module name
            key: Configuration key

        Returns:
            True if deleted successfully, False otherwise
        """
        if not self.enabled or not self._redis_client:
            return False

        try:
            cache_key = self._make_key(tenant_id, module, key)
            self._redis_client.delete(cache_key)
            return True
        except RedisError as e:
            logger.warning(f"Config cache: Failed to delete value: {e}")
            return False

    def invalidate_module(self, tenant_id: UUID, module: str) -> int:
        """Invalidate all cached values for a module.

        Args:
            tenant_id: Tenant ID
            module: Module name

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self._redis_client:
            return 0

        try:
            pattern = self._make_module_pattern(tenant_id, module)

            # Scan for keys matching pattern
            keys_to_delete = []
            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor, match=pattern, count=100
                )
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break

            # Delete keys in batch
            if keys_to_delete:
                return self._redis_client.delete(*keys_to_delete)

            return 0
        except RedisError as e:
            logger.warning(f"Config cache: Failed to invalidate module: {e}")
            return 0

    def clear_all(self) -> bool:
        """Clear all config cache entries.

        WARNING: This clears ALL config cache for all tenants.
        Use with caution.

        Returns:
            True if cleared successfully, False otherwise
        """
        if not self.enabled or not self._redis_client:
            return False

        try:
            # Scan for all config keys
            keys_to_delete = []
            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor, match="config:*", count=1000
                )
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break

            # Delete in batch
            if keys_to_delete:
                self._redis_client.delete(*keys_to_delete)

            logger.info(f"Config cache: Cleared {len(keys_to_delete)} entries")
            return True
        except RedisError as e:
            logger.error(f"Config cache: Failed to clear all: {e}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled or not self._redis_client:
            return {"enabled": False, "status": "disabled"}

        try:
            # Count total config keys
            total_keys = 0
            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(
                    cursor=cursor, match="config:*", count=1000
                )
                total_keys += len(keys)
                if cursor == 0:
                    break

            # Get Redis info
            info = self._redis_client.info("memory")

            return {
                "enabled": True,
                "status": "connected",
                "total_keys": total_keys,
                "ttl": self.ttl,
                "memory_used": info.get("used_memory_human", "unknown"),
            }
        except RedisError as e:
            logger.error(f"Config cache: Failed to get stats: {e}")
            return {
                "enabled": True,
                "status": "error",
                "error": str(e),
            }


# Singleton instance
_cache_instance: ConfigCache | None = None


def get_config_cache(enabled: bool = True, ttl: int = 300) -> ConfigCache:
    """Get or create ConfigCache singleton instance.

    Args:
        enabled: Whether caching is enabled
        ttl: Time-to-live for cached values in seconds

    Returns:
        ConfigCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ConfigCache(enabled=enabled, ttl=ttl)
    return _cache_instance
















