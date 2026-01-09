"""JWT token creation and validation utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt

from app.core.config_file import get_settings

settings = get_settings()


def _encode_jwt(payload: dict[str, Any]) -> str:
    """Encode JWT token with common fields (DRY helper)."""
    to_encode = payload.copy()
    to_encode.update({
        "exp": to_encode.get("exp"),
        "iat": datetime.now(timezone.utc),
        "type": to_encode.get("type", "access")
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing token payload (sub, tenant_id, roles, permissions).
        expires_delta: Optional expiration time delta. Defaults to ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT token string.

    Example:
        >>> data = {"sub": "user_id", "tenant_id": "tenant_id", "roles": ["admin"]}
        >>> token = create_access_token(data)
        >>> len(token) > 0
        True
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "type": "access"})
    return _encode_jwt(to_encode)


def create_refresh_token(
    user_id: UUID,
    remember_me: bool = False,
    expires_at: datetime | None = None,
) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User UUID.
        remember_me: If True, token expires in REFRESH_TOKEN_REMEMBER_ME_DAYS, otherwise REFRESH_TOKEN_EXPIRE_DAYS.

    Returns:
        Encoded JWT refresh token string.

    Example:
        >>> from uuid import uuid4
        >>> user_id = uuid4()
        >>> token = create_refresh_token(user_id)
        >>> len(token) > 0
        True
    """
    if expires_at is None:
        expire_days = settings.REFRESH_TOKEN_REMEMBER_ME_DAYS if remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
        expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    else:
        expire = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid4()),  # Unique identifier for this token
    }
    return _encode_jwt(to_encode)


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode.

    Returns:
        Decoded token payload if valid, None otherwise.

    Example:
        >>> data = {"sub": "user_id"}
        >>> token = create_access_token(data)
        >>> decoded = decode_token(token)
        >>> decoded is not None
        True
        >>> decoded.get("sub") == "user_id"
        True
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """
    Verify a refresh token and return its payload.

    Args:
        token: Refresh token string to verify.

    Returns:
        Decoded token payload if valid and type is 'refresh', None otherwise.

    Example:
        >>> from uuid import uuid4
        >>> user_id = uuid4()
        >>> token = create_refresh_token(user_id)
        >>> payload = verify_refresh_token(token)
        >>> payload is not None
        True
        >>> payload.get("type") == "refresh"
        True
    """
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.get("type") != "refresh":
        return None
    return payload
