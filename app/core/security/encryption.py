"""Encryption utilities for secure credential storage."""

import base64
import hashlib
import hmac
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken

from app.core.config_file import get_settings


def get_encryption_key(tenant_id: UUID) -> bytes:
    """Get encryption key for a specific tenant.

    The key is derived from SECRET_KEY and tenant_id using HMAC-SHA256.
    This ensures:
    - Each tenant has a unique encryption key
    - The same tenant always gets the same key
    - Keys are deterministic but secure

    Args:
        tenant_id: Tenant UUID

    Returns:
        Encryption key as bytes (32 bytes for Fernet)
    """
    settings = get_settings()
    secret_key = settings.SECRET_KEY

    # Create tenant-specific secret
    tenant_secret = f"{tenant_id}:{secret_key}"

    # Derive key using HMAC-SHA256
    key_hash = hmac.new(
        secret_key.encode(),
        tenant_secret.encode(),
        hashlib.sha256
    ).digest()

    # Fernet requires a URL-safe base64-encoded 32-byte key
    # Use the hash directly (it's already 32 bytes)
    return base64.urlsafe_b64encode(key_hash)


def encrypt_credentials(data: str, tenant_id: UUID) -> str:
    """Encrypt credentials for a tenant.

    Uses Fernet (symmetric encryption) with a tenant-specific key.

    Args:
        data: Plain text data to encrypt (typically JSON string)
        tenant_id: Tenant UUID for key derivation

    Returns:
        Encrypted data as base64-encoded string

    Raises:
        ValueError: If encryption fails
    """
    if not data:
        return ""

    try:
        key = get_encryption_key(tenant_id)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(data.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to encrypt credentials: {str(e)}") from e


def decrypt_credentials(encrypted_data: str, tenant_id: UUID) -> str:
    """Decrypt credentials for a tenant.

    Uses Fernet (symmetric encryption) with a tenant-specific key.

    Args:
        encrypted_data: Encrypted data as base64-encoded string
        tenant_id: Tenant UUID for key derivation

    Returns:
        Decrypted plain text data

    Raises:
        ValueError: If decryption fails (invalid data, wrong tenant, etc.)
    """
    if not encrypted_data:
        return ""

    try:
        key = get_encryption_key(tenant_id)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted.decode('utf-8')
    except InvalidToken:
        raise ValueError("Invalid encrypted data or wrong tenant key") from None
    except Exception as e:
        raise ValueError(f"Failed to decrypt credentials: {str(e)}") from e











