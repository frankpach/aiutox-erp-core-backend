"""Password hashing and verification utilities using bcrypt."""

import bcrypt

# bcrypt cost factor 12+ (OWASP recommendation)
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash.

    Returns:
        Hashed password string.

    Example:
        >>> hashed = hash_password("my_password")
        >>> len(hashed) > 0
        True
    """
    # Encode password to bytes
    password_bytes = password.encode("utf-8")
    # Generate salt and hash
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string (bcrypt returns bytes)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to compare against.

    Returns:
        True if password matches, False otherwise.

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    try:
        # Encode to bytes
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        # Verify password
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except (ValueError, TypeError):
        # Handle invalid hash format
        return False
