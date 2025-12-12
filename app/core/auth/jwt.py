"""JWT token creation and validation utilities."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt

from app.core.config_file import get_settings

settings = get_settings()


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
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: UUID) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User UUID.

    Returns:
        Encoded JWT refresh token string.

    Example:
        >>> from uuid import uuid4
        >>> user_id = uuid4()
        >>> token = create_refresh_token(user_id)
        >>> len(token) > 0
        True
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


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
