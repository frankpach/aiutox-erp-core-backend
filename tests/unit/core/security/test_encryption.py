"""Unit tests for encryption module."""

import json
import pytest
from uuid import uuid4

from app.core.security.encryption import (
    decrypt_credentials,
    encrypt_credentials,
    get_encryption_key,
)


class TestEncryption:
    """Test encryption and decryption functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypting and decrypting returns the same value."""
        tenant_id = uuid4()
        original_data = '{"api_key": "sk_test_1234567890", "secret": "secret_key"}'

        encrypted = encrypt_credentials(original_data, tenant_id)
        decrypted = decrypt_credentials(encrypted, tenant_id)

        assert decrypted == original_data
        assert encrypted != original_data  # Should be different

    def test_encrypt_different_tenants(self):
        """Test that same text encrypted for different tenants gives different results."""
        tenant1 = uuid4()
        tenant2 = uuid4()
        original_data = '{"api_key": "sk_test_1234567890"}'

        encrypted1 = encrypt_credentials(original_data, tenant1)
        encrypted2 = encrypt_credentials(original_data, tenant2)

        # Encrypted data should be different
        assert encrypted1 != encrypted2

        # But both should decrypt to the same value with their respective tenants
        decrypted1 = decrypt_credentials(encrypted1, tenant1)
        decrypted2 = decrypt_credentials(encrypted2, tenant2)

        assert decrypted1 == original_data
        assert decrypted2 == original_data

    def test_decrypt_invalid_data(self):
        """Test that decrypting invalid data raises an exception."""
        tenant_id = uuid4()
        invalid_data = "not_valid_encrypted_data"

        with pytest.raises(ValueError, match="Invalid encrypted data"):
            decrypt_credentials(invalid_data, tenant_id)

    def test_decrypt_wrong_tenant(self):
        """Test that decrypting with wrong tenant fails."""
        tenant1 = uuid4()
        tenant2 = uuid4()
        original_data = '{"api_key": "sk_test_1234567890"}'

        encrypted = encrypt_credentials(original_data, tenant1)

        # Should fail when trying to decrypt with different tenant
        with pytest.raises(ValueError, match="Invalid encrypted data or wrong tenant key"):
            decrypt_credentials(encrypted, tenant2)

    def test_encrypt_empty_string(self):
        """Test handling of empty strings."""
        tenant_id = uuid4()
        original_data = ""

        encrypted = encrypt_credentials(original_data, tenant_id)
        decrypted = decrypt_credentials(encrypted, tenant_id)

        assert decrypted == original_data

    def test_encrypt_special_characters(self):
        """Test handling of special characters and Unicode."""
        tenant_id = uuid4()
        original_data = '{"api_key": "sk_test_123", "message": "Hello 世界 🌍", "special": "!@#$%^&*()"}'

        encrypted = encrypt_credentials(original_data, tenant_id)
        decrypted = decrypt_credentials(encrypted, tenant_id)

        assert decrypted == original_data

    def test_encrypt_json_object(self):
        """Test encrypting a JSON object string."""
        tenant_id = uuid4()
        credentials_dict = {
            "api_key": "sk_test_1234567890",
            "api_secret": "secret_abc123",
            "webhook_secret": "whsec_xyz789"
        }
        original_data = json.dumps(credentials_dict)

        encrypted = encrypt_credentials(original_data, tenant_id)
        decrypted = decrypt_credentials(encrypted, tenant_id)
        decrypted_dict = json.loads(decrypted)

        assert decrypted_dict == credentials_dict

    def test_get_encryption_key_consistency(self):
        """Test that get_encryption_key returns the same key for the same tenant."""
        tenant_id = uuid4()

        key1 = get_encryption_key(tenant_id)
        key2 = get_encryption_key(tenant_id)

        assert key1 == key2

    def test_get_encryption_key_different_tenants(self):
        """Test that different tenants get different keys."""
        tenant1 = uuid4()
        tenant2 = uuid4()

        key1 = get_encryption_key(tenant1)
        key2 = get_encryption_key(tenant2)

        assert key1 != key2

