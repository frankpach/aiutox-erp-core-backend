"""Authentication and authorization core module."""

from app.core.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_refresh_token,
)
from app.core.auth.password import hash_password, verify_password
from app.core.auth.rate_limit import (
    check_login_rate_limit,
    create_rate_limit_exception,
    limiter,
    record_login_attempt,
)
from app.core.auth.token_hash import hash_token, verify_token

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_refresh_token",
    "hash_password",
    "verify_password",
    "check_login_rate_limit",
    "create_rate_limit_exception",
    "limiter",
    "record_login_attempt",
    "hash_token",
    "verify_token",
]
