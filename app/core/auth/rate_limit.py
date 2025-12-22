"""Rate limiting utilities for authentication endpoints."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config_file import get_settings
from app.core.exceptions import APIException
from fastapi import status

settings = get_settings()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


def get_rate_limit_exceeded_handler() -> Callable:
    """
    Get rate limit exceeded exception handler.

    Returns:
        Exception handler function for rate limit exceeded errors.
    """
    return _rate_limit_exceeded_handler


def create_rate_limit_exception() -> APIException:
    """
    Create a rate limit exceeded API exception.

    Returns:
        APIException with appropriate error format.

    Example:
        >>> exc = create_rate_limit_exception()
        >>> exc.status_code == 429
        True
    """
    return APIException(
        code="AUTH_RATE_LIMIT_EXCEEDED",
        message="Too many requests. Please try again later.",
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    )


# Simple in-memory rate limiter for login (5 attempts per minute per IP)
# In production, consider using Redis for distributed rate limiting
_login_attempts: dict[str, list[datetime]] = defaultdict(list)


def check_login_rate_limit(ip_address: str, max_attempts: int = 5, window_minutes: int = 1) -> bool:
    """
    Check if login rate limit is exceeded for an IP address.

    IMPORTANT: This function only checks the limit, it does NOT record attempts.
    Use record_login_attempt() to record failed attempts.

    Args:
        ip_address: Client IP address.
        max_attempts: Maximum number of attempts allowed.
        window_minutes: Time window in minutes.

    Returns:
        True if rate limit is not exceeded, False otherwise.

    Example:
        >>> ip = "127.0.0.1"
        >>> check_login_rate_limit(ip, max_attempts=5)
        True
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=window_minutes)

    # Clean old attempts
    attempts = _login_attempts[ip_address]
    attempts[:] = [attempt for attempt in attempts if attempt > window_start]

    # Check if limit exceeded
    if len(attempts) >= max_attempts:
        return False

    # DO NOT record attempt here - only check the limit
    # Attempts are recorded separately via record_login_attempt() for failed logins only
    return True


def record_login_attempt(ip_address: str) -> None:
    """
    Record a login attempt for rate limiting.

    Args:
        ip_address: Client IP address.

    Example:
        >>> record_login_attempt("127.0.0.1")
    """
    now = datetime.now(timezone.utc)
    _login_attempts[ip_address].append(now)


def clear_successful_login(ip_address: str) -> None:
    """
    Clear rate limit for successful login.
    Successful logins should not count towards rate limiting.

    Args:
        ip_address: Client IP address.

    Example:
        >>> clear_successful_login("127.0.0.1")
    """
    # Remove the last attempt (which was successful)
    if ip_address in _login_attempts and _login_attempts[ip_address]:
        _login_attempts[ip_address].pop()

    # If no attempts remain, remove the IP from the dict
    if ip_address in _login_attempts and not _login_attempts[ip_address]:
        del _login_attempts[ip_address]
