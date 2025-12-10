"""Token hashing utilities for refresh tokens.

JWT tokens are typically longer than 72 bytes (bcrypt limit), so we use
SHA256 to hash them first, then bcrypt for additional security.
"""

import hashlib

from app.core.auth.password import hash_password, verify_password


def hash_token(token: str) -> str:
    """
    Hash a token (typically JWT refresh token) for storage.

    Since JWT tokens are longer than 72 bytes (bcrypt limit), we first
    hash with SHA256, then use bcrypt for additional security.

    Args:
        token: Token string to hash (typically JWT refresh token).

    Returns:
        Hashed token string (bcrypt hash of SHA256 hash).

    Example:
        >>> token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        >>> hashed = hash_token(token)
        >>> len(hashed) > 0
        True
    """
    # First hash with SHA256 (handles tokens of any length)
    sha256_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # Then hash with bcrypt (for additional security and slow hashing)
    return hash_password(sha256_hash)


def verify_token(token: str, hashed_token: str) -> bool:
    """
    Verify a token against its hash.

    Args:
        token: Plain token string to verify.
        hashed_token: Hashed token to compare against.

    Returns:
        True if token matches, False otherwise.

    Example:
        >>> token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        >>> hashed = hash_token(token)
        >>> verify_token(token, hashed)
        True
        >>> verify_token("wrong_token", hashed)
        False
    """
    # Hash the provided token the same way
    sha256_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # Verify against stored hash
    return verify_password(sha256_hash, hashed_token)

