"""Retry logic with exponential backoff."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


def calculate_backoff(attempt: int) -> float:
    """Calculate exponential backoff delay in seconds.

    Args:
        attempt: Current attempt number (0-indexed)

    Returns:
        Delay in seconds (1s, 2s, 4s, 8s, 16s)
    """
    return min(2**attempt, 16.0)


def should_retry(attempt: int, max_attempts: int = 5) -> bool:
    """Check if we should retry based on attempt number.

    Args:
        attempt: Current attempt number (0-indexed)
        max_attempts: Maximum number of attempts

    Returns:
        True if should retry, False otherwise
    """
    return attempt < max_attempts


class RetryHandler:
    """Handler for retrying operations with exponential backoff."""

    def __init__(self, max_attempts: int = 5):
        """Initialize retry handler.

        Args:
            max_attempts: Maximum number of retry attempts
        """
        self.max_attempts = max_attempts

    async def retry_with_backoff(
        self,
        callback: Callable[[], Awaitable[Any]],
        operation_name: str = "operation",
    ) -> Any:
        """Retry an async operation with exponential backoff.

        Args:
            callback: Async function to retry
            operation_name: Name of the operation for logging

        Returns:
            Result of the callback

        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return await callback()
            except Exception as e:
                last_exception = e
                if not should_retry(attempt, self.max_attempts):
                    logger.error(
                        f"{operation_name} failed after {self.max_attempts} attempts: {e}",
                        exc_info=True,
                    )
                    raise

                delay = calculate_backoff(attempt)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{self.max_attempts}): {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception

        raise RuntimeError(f"{operation_name} failed: unknown error")
