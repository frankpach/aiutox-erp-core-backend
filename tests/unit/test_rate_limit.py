"""Unit tests for rate limiting utilities."""

import time
from datetime import datetime, timedelta, timezone

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

    # Make 5 attempts (at limit)
    for i in range(5):
        result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
        assert result is True

    # 6th attempt should exceed limit
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is False


def test_check_login_rate_limit_cleans_old_attempts():
    """Test that check_login_rate_limit cleans old attempts outside window."""
    ip_address = "127.0.0.1"

    # Manually add old attempts (outside 1 minute window)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
    _login_attempts[ip_address] = [old_time, old_time, old_time]

    # Should clean old attempts and allow new ones
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is True

    # Verify old attempts were cleaned
    attempts = _login_attempts[ip_address]
    assert len(attempts) == 1  # Only the new attempt
    assert all(attempt > datetime.now(timezone.utc) - timedelta(minutes=1) for attempt in attempts)


def test_check_login_rate_limit_per_ip():
    """Test that rate limiting is per IP address."""
    ip1 = "127.0.0.1"
    ip2 = "192.168.1.1"

    # Exceed limit for IP1
    for i in range(5):
        check_login_rate_limit(ip1, max_attempts=5, window_minutes=1)

    # IP1 should be rate limited
    result1 = check_login_rate_limit(ip1, max_attempts=5, window_minutes=1)
    assert result1 is False

    # IP2 should not be rate limited
    result2 = check_login_rate_limit(ip2, max_attempts=5, window_minutes=1)
    assert result2 is True


def test_check_login_rate_limit_custom_max_attempts():
    """Test that check_login_rate_limit respects custom max_attempts."""
    ip_address = "127.0.0.1"

    # Make 2 attempts with max_attempts=3
    for i in range(2):
        result = check_login_rate_limit(ip_address, max_attempts=3, window_minutes=1)
        assert result is True

    # 3rd attempt should still pass
    result = check_login_rate_limit(ip_address, max_attempts=3, window_minutes=1)
    assert result is True

    # 4th attempt should exceed limit
    result = check_login_rate_limit(ip_address, max_attempts=3, window_minutes=1)
    assert result is False


def test_check_login_rate_limit_window_reset():
    """Test that rate limit resets after window expires."""
    ip_address = "127.0.0.1"

    # Exceed limit
    for i in range(5):
        check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)

    # Should be rate limited
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
    before = datetime.now(timezone.utc)

    record_login_attempt(ip_address)

    after = datetime.now(timezone.utc)

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
    assert exc.detail["error"]["message"] == "Too many requests. Please try again later."
    assert exc.detail["error"]["details"] is None


def test_check_login_rate_limit_integration():
    """Integration test: check and record work together."""
    ip_address = "127.0.0.1"

    # Use check which also records
    for i in range(4):
        result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
        assert result is True

    # Manually record one more (simulating failed login)
    record_login_attempt(ip_address)

    # Now check should fail
    result = check_login_rate_limit(ip_address, max_attempts=5, window_minutes=1)
    assert result is False

