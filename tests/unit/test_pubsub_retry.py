"""Unit tests for Pub-Sub retry logic."""

import asyncio
import pytest

from app.core.pubsub.retry import RetryHandler, calculate_backoff, should_retry


def test_calculate_backoff():
    """Test exponential backoff calculation."""
    assert calculate_backoff(0) == 1.0
    assert calculate_backoff(1) == 2.0
    assert calculate_backoff(2) == 4.0
    assert calculate_backoff(3) == 8.0
    assert calculate_backoff(4) == 16.0
    assert calculate_backoff(5) == 16.0  # Capped at 16
    assert calculate_backoff(10) == 16.0  # Capped at 16


def test_should_retry():
    """Test should_retry logic."""
    assert should_retry(0, max_attempts=5) is True
    assert should_retry(1, max_attempts=5) is True
    assert should_retry(2, max_attempts=5) is True
    assert should_retry(3, max_attempts=5) is True
    assert should_retry(4, max_attempts=5) is True
    assert should_retry(5, max_attempts=5) is False
    assert should_retry(6, max_attempts=5) is False


@pytest.mark.asyncio
async def test_retry_handler_success():
    """Test RetryHandler with successful operation."""
    handler = RetryHandler(max_attempts=5)
    call_count = 0

    async def successful_callback():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await handler.retry_with_backoff(successful_callback, "test_operation")

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_handler_retry_success():
    """Test RetryHandler with retry that eventually succeeds."""
    handler = RetryHandler(max_attempts=5)
    call_count = 0

    async def retry_callback():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"

    result = await handler.retry_with_backoff(retry_callback, "test_operation")

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_handler_max_attempts():
    """Test RetryHandler exhausts all retries."""
    handler = RetryHandler(max_attempts=3)
    call_count = 0

    async def failing_callback():
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fails")

    with pytest.raises(ValueError, match="Always fails"):
        await handler.retry_with_backoff(failing_callback, "test_operation")

    assert call_count == 3  # Should try 3 times


@pytest.mark.asyncio
async def test_retry_handler_backoff_timing():
    """Test that retry handler uses backoff delays."""
    handler = RetryHandler(max_attempts=3)
    call_times = []

    async def failing_callback():
        call_times.append(asyncio.get_event_loop().time())
        raise ValueError("Always fails")

    start_time = asyncio.get_event_loop().time()

    with pytest.raises(ValueError):
        await handler.retry_with_backoff(failing_callback, "test_operation")

    # Verify delays between calls (allowing some tolerance)
    if len(call_times) >= 2:
        delay1 = call_times[1] - call_times[0]
        assert delay1 >= 0.9  # Should be ~1 second (with tolerance)

    if len(call_times) >= 3:
        delay2 = call_times[2] - call_times[1]
        assert delay2 >= 1.9  # Should be ~2 seconds (with tolerance)









