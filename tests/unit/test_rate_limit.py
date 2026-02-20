"""Unit tests for rate limiting utilities."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException, status

from app.core.auth.rate_limit import (
    _login_attempts,
    check_login_rate_limit,
    create_rate_limit_exception,
    record_login_attempt,
)


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    """Clear rate limit state before each test."""
    _login_attempts.clear()
    yield
    _login_attempts.clear()


def test_check_login_rate_limit_not_exceeded():
    """Test that check_login_rate_limit returns True when limit is not exceeded."""
    ip_address = "127.0.0.1"

    # Make 4 attempts (below limit of 5)
    for i in range(4):
        result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
        assert result is True

    # Should still be under limit
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is True


def test_check_login_rate_limit_exceeded():
    """Test that check_login_rate_limit returns False when limit is exceeded."""
    ip_address = "127.0.0.1"

    # Record 5 attempts (at limit)
    for i in range(5):
        record_login_attempt(ip_address)

    # Should be at limit (not under)
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is False

    # Record 6th attempt (exceeds limit)
    record_login_attempt(ip_address)

    # Now should be rate limited
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is False


def test_check_login_rate_limit_cleans_old_attempts():
    """Test that check_login_rate_limit cleans old attempts outside window."""
    ip_address = "127.0.0.1"

    # Manually add old attempts (outside 1 minute window)
    old_time = datetime.now(UTC) - timedelta(minutes=2)
    _login_attempts[ip_address] = [old_time, old_time, old_time]

    # Should clean old attempts and allow new ones
    record_login_attempt(ip_address)
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is True

    # Verify old attempts were cleaned (only the new attempt should remain)
    attempts = _login_attempts[ip_address]
    assert len(attempts) == 1  # Only the new attempt
    assert all(
        attempt > datetime.now(UTC) - timedelta(minutes=1) for attempt in attempts
    )


def test_check_login_rate_limit_per_ip():
    """Test that rate limiting is per IP address."""
    ip1 = "127.0.0.1"
    ip2 = "192.168.1.1"

    # Exceed limit for IP1
    for i in range(5):
        record_login_attempt(ip1)
        check_login_rate_limit(ip1, max_attempts=5, window_minutes=1)

    # IP1 should be rate limited
    record_login_attempt(ip1)
    result1 = check_login_rate_limit(ip1, max_attempts=5, window_minutes=1)
    assert result1 is False

    # IP2 should not be rate limited
    result2 = check_login_rate_limit(ip2, max_attempts=5, window_minutes=1)
    assert result2 is True


def test_check_login_rate_limit_custom_max_attempts():
    """Test that check_login_rate_limit respects custom max_attempts."""
    ip_address = "127.0.0.1"

    # Record 2 attempts with max_attempts=3
    for i in range(2):
        record_login_attempt(ip_address)

    # Should still be under limit
    result = check_login_rate_limit(ip_address, max_attempts=3, window_minutes=1)
    assert result is True

    # Record 3rd attempt
    record_login_attempt(ip_address)

    # Should be at limit (3 attempts with max_attempts=3)
    result = check_login_rate_limit(ip_address, max_attempts=3, window_minutes=1)
    assert result is False

    # Record 4th attempt (exceeds limit)
    record_login_attempt(ip_address)

    # Now should be rate limited
    result = check_login_rate_limit(ip_address, max_attempts=3, window_minutes=1)
    assert result is False


def test_check_login_rate_limit_window_reset():
    """Test that rate limit resets after window expires."""
    ip_address = "127.0.0.1"

    # Exceed limit
    for i in range(5):
        record_login_attempt(ip_address)
        check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)

    # Should be rate limited
    record_login_attempt(ip_address)
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is False

    # Clear attempts and simulate window reset
    _login_attempts.clear()

    # Should work again after reset
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is True


def test_record_login_attempt():
    """Test that record_login_attempt records attempt correctly."""
    ip_address = "127.0.0.1"

    # Record attempt
    record_login_attempt(ip_address)

    # Verify attempt was recorded
    assert ip_address in _login_attempts
    assert len(_login_attempts[ip_address]) == 1

    # Record another attempt
    record_login_attempt(ip_address)

    # Verify both attempts recorded
    assert len(_login_attempts[ip_address]) == 2


def test_record_login_attempt_multiple_ips():
    """Test that record_login_attempt works for multiple IPs."""
    ip1 = "127.0.0.1"
    ip2 = "192.168.1.1"

    # Record attempts for both IPs
    record_login_attempt(ip1)
    record_login_attempt(ip2)
    record_login_attempt(ip1)

    # Verify both IPs have correct counts
    assert len(_login_attempts[ip1]) == 2
    assert len(_login_attempts[ip2]) == 1


def test_record_login_attempt_timestamp():
    """Test that record_login_attempt records correct timestamp."""
    ip_address = "127.0.0.1"
    before = datetime.now(UTC)

    record_login_attempt(ip_address)

    after = datetime.now(UTC)

    # Verify timestamp is within reasonable range
    attempts = _login_attempts[ip_address]
    assert len(attempts) == 1
    attempt_time = attempts[0]
    assert before <= attempt_time <= after


def test_create_rate_limit_exception():
    """Test that create_rate_limit_exception creates correct exception."""
    exc = create_rate_limit_exception()

    assert isinstance(exc, HTTPException)
    assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "error" in exc.detail
    assert exc.detail["error"]["code"] == "AUTH_RATE_LIMIT_EXCEEDED"
    assert (
        exc.detail["error"]["message"] == "Too many requests. Please try again later."
    )
    assert exc.detail["error"]["details"] is None


def test_check_login_rate_limit_integration():
    """Integration test: check and record work together."""
    ip_address = "127.0.0.1"

    # Record 4 attempts
    for i in range(4):
        record_login_attempt(ip_address)
        result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
        assert result is True

    # Record 5th attempt (at limit)
    record_login_attempt(ip_address)
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is False

    # Record 6th attempt (exceeds limit)
    record_login_attempt(ip_address)
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is False
