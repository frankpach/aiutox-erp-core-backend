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

    def test_set_config_with_audit_log(self, db_session: Session, test_tenant, test_user):
        """Test setting configuration with audit logging."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "audit_test"
        key = "audit_key"
        value = "test_value"

        result = service.set(
            tenant_id,
            module,
            key,
            value,
            user_id=test_user.id,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert result["value"] == value

        # Verify audit log was created
        from app.models.audit_log import AuditLog
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.action == "config.created",
            AuditLog.resource_type == "config",
        ).all()
        assert len(audit_logs) > 0

    def test_set_config_with_versioning(self, db_session: Session, test_tenant, test_user):
        """Test setting configuration with versioning enabled."""
        service = ConfigService(db_session, use_versioning=True)
        tenant_id = test_tenant.id
        module = "version_test"
        key = "version_key"

        # Create first version
        service.set(tenant_id, module, key, "value1", user_id=test_user.id)

        # Update to create second version
        service.set(tenant_id, module, key, "value2", user_id=test_user.id)

        # Get version history
        versions, total = service.get_version_history(tenant_id, module, key)
        assert total >= 2
        assert len(versions) >= 2

    def test_rollback_to_version(self, db_session: Session, test_tenant, test_user):
        """Test rolling back to a previous version."""
        service = ConfigService(db_session, use_versioning=True)
        tenant_id = test_tenant.id
        module = "rollback_test"
        key = "rollback_key"

        # Create initial version
        service.set(tenant_id, module, key, "initial", user_id=test_user.id)

        # Update to version 2
        service.set(tenant_id, module, key, "updated", user_id=test_user.id)

        # Rollback to version 1
        result = service.rollback_to_version(
            tenant_id, module, key, version_number=1, user_id=test_user.id
        )

        # Verify rollback
        assert result["value"] == "initial"
        current_value = service.get(tenant_id, module, key)
        assert current_value == "initial"

    def test_service_without_cache(self, db_session: Session, test_tenant):
        """Test service behavior without cache."""
        service = ConfigService(db_session, use_cache=False)
        tenant_id = test_tenant.id
        module = "no_cache_test"
        key = "no_cache_key"
        value = "test_value"

        # Set and get should work without cache
        service.set(tenant_id, module, key, value)
        result = service.get(tenant_id, module, key)
        assert result == value

        # Cache stats should show disabled
        stats = service.get_cache_stats()
        assert stats["enabled"] is False

    def test_service_without_versioning(self, db_session: Session, test_tenant, test_user):
        """Test service behavior without versioning."""
        service = ConfigService(db_session, use_versioning=False)
        tenant_id = test_tenant.id
        module = "no_version_test"
        key = "no_version_key"

        # Set should work without versioning
        service.set(tenant_id, module, key, "value1", user_id=test_user.id)

        # Version history should be empty
        versions, total = service.get_version_history(tenant_id, module, key)
        assert total == 0
        assert len(versions) == 0

        # Rollback should raise error
        with pytest.raises(ValueError, match="Versioning is not enabled"):
            service.rollback_to_version(tenant_id, module, key, version_number=1)

    def test_delete_config_with_audit(self, db_session: Session, test_tenant, test_user):
        """Test deleting configuration with audit logging."""
        service = ConfigService(db_session)
        tenant_id = test_tenant.id
        module = "delete_audit_test"
        key = "delete_key"

        # Create first
        service.set(tenant_id, module, key, "value", user_id=test_user.id)

        # Delete it
        service.delete(
            tenant_id,
            module,
            key,
            user_id=test_user.id,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        # Verify it's gone
        result = service.get(tenant_id, module, key)
        assert result is None

        # Verify audit log was created
        from app.models.audit_log import AuditLog
        audit_logs = db_session.query(AuditLog).filter(
            AuditLog.action == "config.deleted",
            AuditLog.resource_type == "config",
        ).all()
        assert len(audit_logs) > 0

    def test_cleanup_old_versions(self, db_session: Session, test_tenant, test_user):
        """Test cleaning up old versions."""
        service = ConfigService(db_session, use_versioning=True)
        tenant_id = test_tenant.id
        module = "cleanup_test"
        key = "cleanup_key"

        # Create multiple versions
        for i in range(15):
            service.set(tenant_id, module, key, f"value{i}", user_id=test_user.id)

        # Cleanup, keeping only 10 versions
        deleted_count = service.cleanup_old_versions(tenant_id, module, key, keep_versions=10)

        # Verify cleanup happened
        assert deleted_count > 0

        # Verify we still have versions
        versions, total = service.get_version_history(tenant_id, module, key)
        assert total <= 10











