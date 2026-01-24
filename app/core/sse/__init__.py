"""SSE module for real-time notifications."""

from app.core.sse.manager import SSEConnectionManager, get_sse_manager

__all__ = ["SSEConnectionManager", "get_sse_manager"]
