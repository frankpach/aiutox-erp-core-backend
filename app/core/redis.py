"""Redis client configuration and utilities."""

import redis.asyncio as redis

from app.core.config_file import get_settings

# Global Redis client instance
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """
    Obtiene la instancia global del cliente Redis.

    Returns:
        Instancia singleton del cliente Redis
    """
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = await redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client():
    """Cierra la conexión del cliente Redis."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
