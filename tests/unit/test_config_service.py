"""Unit tests for ConfigService."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.config.schema import config_schema
from app.core.config.service import ConfigService


class TestConfigService:
    """Test suite for ConfigService."""

    def test_get_config_existing(self, db_session: Session, test_tenant):
        """Test getting an existing configuration."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"
        value = 10.0

        # Create first
        service.set(tenant_id, module, key, value)

        # Get it
        result = service.get(tenant_id, module, key)

        assert result == value

    def test_get_config_not_found_with_default(self, db_session: Session, test_tenant):
        """Test getting a non-existent configuration with default."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id

        result = service.get(tenant_id, "products", "nonexistent", default=5.0)

        assert result == 5.0

    def test_get_config_not_found_without_default(self, db_session: Session, test_tenant):
        """Test getting a non-existent configuration without default."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id

        result = service.get(tenant_id, "products", "nonexistent")

        assert result is None

    def test_get_config_with_schema_default(self, db_session: Session, test_tenant):
        """Test getting a configuration that uses schema default."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"

        # Register schema with default
        config_schema.register_schema(
            module, key, {"type": "float", "default": 5.0, "required": False}
        )

        # Get it (should return schema default)
        result = service.get(tenant_id, module, key)

        assert result == 5.0

    def test_set_config_new(self, db_session: Session, test_tenant):
        """Test setting a new configuration."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"
        value = 10.0

        result = service.set(tenant_id, module, key, value)

        assert result["module"] == module
        assert result["key"] == key
        assert result["value"] == value

        # Verify it was saved
        retrieved = service.get(tenant_id, module, key)
        assert retrieved == value

    def test_set_config_update(self, db_session: Session, test_tenant):
        """Test updating an existing configuration."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"

        # Create first
        service.set(tenant_id, module, key, 10.0)

        # Update it
        service.set(tenant_id, module, key, 20.0)

        # Verify update
        result = service.get(tenant_id, module, key)
        assert result == 20.0

    def test_set_config_validation_fails(self, db_session: Session, test_tenant):
        """Test setting a configuration that fails validation."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"

        # Register schema that requires int
        config_schema.register_schema(
            module, key, {"type": "int", "default": 0, "required": False}
        )

        # Try to set string (should fail validation and raise ValueError)
        with pytest.raises(ValueError, match="Invalid value for products.min_price"):
            service.set(tenant_id, module, key, "invalid")

    def test_get_module_config(self, db_session: Session, test_tenant):
        """Test getting all configuration for a module."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "test_module"  # Use different module to avoid schema conflicts

        # Create multiple configs
        service.set(tenant_id, module, "min_price", 10.0)
        service.set(tenant_id, module, "max_price", 100.0)
        service.set(tenant_id, "inventory", "min_stock", 5)  # Different module

        result = service.get_module_config(tenant_id, module)

        assert len(result) == 2
        assert result["min_price"] == 10.0
        assert result["max_price"] == 100.0
        assert "min_stock" not in result

    def test_set_module_config(self, db_session: Session, test_tenant):
        """Test setting multiple configuration values."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "test_module"  # Use different module to avoid schema conflicts
        config_dict = {"min_price": 10.0, "max_price": 100.0, "currency": "USD"}

        result = service.set_module_config(tenant_id, module, config_dict)

        assert result == config_dict

        # Verify individual values
        assert service.get(tenant_id, module, "min_price") == 10.0
        assert service.get(tenant_id, module, "max_price") == 100.0
        assert service.get(tenant_id, module, "currency") == "USD"

    def test_delete_config(self, db_session: Session, test_tenant):
        """Test deleting a configuration."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "test_module"  # Use different module to avoid schema conflicts
        key = "test_key"

        # Create first
        service.set(tenant_id, module, key, 10.0)

        # Delete it
        service.delete(tenant_id, module, key)

        # Verify it's gone (should return None, not schema default)
        result = service.get(tenant_id, module, key)
        assert result is None

    def test_validate_schema(self, db_session: Session):
        """Test schema validation."""
        service = ConfigService(db_session)
        module = "test_module"
        key = "test_key"

        # Register schema
        config_schema.register_schema(
            module, key, {"type": "float", "default": 0.0, "required": False}
        )

        # Valid value
        assert service.validate_schema(module, key, 10.0) is True

        # Invalid value (string instead of float) - should return False
        assert service.validate_schema(module, key, "invalid") is False

    def test_multi_tenant_isolation(self, db_session: Session, test_tenant):
        """Test that configurations are isolated by tenant."""
        service = ConfigService(db_session)
        tenant_id_1 = test_tenant.id
        tenant_id_2 = uuid4()
        module = "isolation_test"  # Use different module to avoid schema conflicts
        key = "isolation_key"

        # Create config for tenant 1
        service.set(tenant_id_1, module, key, 10.0)

        # Should not find it for tenant 2 (should return None, not schema default)
        # Note: get() may return schema default if one is registered, so we check repository directly
        from app.repositories.config_repository import ConfigRepository
        repo = ConfigRepository(db_session)
        config_tenant_2 = repo.get(tenant_id_2, module, key)
        assert config_tenant_2 is None

        # Should exist for tenant 1
        assert service.get(tenant_id_1, module, key) == 10.0




