"""Unit tests for ConfigRepository."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.repositories.config_repository import ConfigRepository


class TestConfigRepository:
    """Test suite for ConfigRepository."""

    def test_create_config(self, db_session: Session, test_tenant):
        """Test creating a configuration entry."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"
        value = 10.0

        config = repo.create(tenant_id, module, key, value)

        assert config is not None
        assert config.tenant_id == tenant_id
        assert config.module == module
        assert config.key == key
        assert config.value == value
        assert config.id is not None

    def test_get_config(self, db_session: Session, test_tenant):
        """Test getting a configuration entry."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"
        value = 10.0

        # Create first
        repo.create(tenant_id, module, key, value)

        # Get it
        config = repo.get(tenant_id, module, key)

        assert config is not None
        assert config.value == value

    def test_get_config_not_found(self, db_session: Session, test_tenant):
        """Test getting a non-existent configuration."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id

        config = repo.get(tenant_id, "products", "nonexistent")

        assert config is None

    def test_get_all_by_module(self, db_session: Session, test_tenant):
        """Test getting all configurations for a module."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id
        module = "products"

        # Create multiple configs
        repo.create(tenant_id, module, "min_price", 10.0)
        repo.create(tenant_id, module, "max_price", 100.0)
        repo.create(tenant_id, "inventory", "min_stock", 5)  # Different module

        configs = repo.get_all_by_module(tenant_id, module)

        assert len(configs) == 2
        assert all(c.module == module for c in configs)

    def test_update_config(self, db_session: Session, test_tenant):
        """Test updating a configuration entry."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"

        # Create first
        repo.create(tenant_id, module, key, 10.0)

        # Update it
        updated = repo.update(tenant_id, module, key, 20.0)

        assert updated.value == 20.0

    def test_update_config_not_found(self, db_session: Session, test_tenant):
        """Test updating a non-existent configuration."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id

        with pytest.raises(ValueError, match="Configuration not found"):
            repo.update(tenant_id, "products", "nonexistent", 10.0)

    def test_delete_config(self, db_session: Session, test_tenant):
        """Test deleting a configuration entry."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"

        # Create first
        repo.create(tenant_id, module, key, 10.0)

        # Delete it
        repo.delete(tenant_id, module, key)

        # Verify it's gone
        config = repo.get(tenant_id, module, key)
        assert config is None

    def test_delete_config_not_found(self, db_session: Session, test_tenant):
        """Test deleting a non-existent configuration (should not raise)."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id

        # Should not raise
        repo.delete(tenant_id, "products", "nonexistent")

    def test_exists(self, db_session: Session, test_tenant):
        """Test checking if a configuration exists."""
        repo = ConfigRepository(db_session)
        tenant_id = test_tenant.id
        module = "products"
        key = "min_price"

        # Should not exist initially
        assert repo.exists(tenant_id, module, key) is False

        # Create it
        repo.create(tenant_id, module, key, 10.0)

        # Should exist now
        assert repo.exists(tenant_id, module, key) is True

    def test_multi_tenant_isolation(self, db_session: Session, test_tenant):
        """Test that configurations are isolated by tenant."""
        repo = ConfigRepository(db_session)
        tenant_id_1 = test_tenant.id
        tenant_id_2 = uuid4()
        module = "products"
        key = "min_price"

        # Create config for tenant 1
        repo.create(tenant_id_1, module, key, 10.0)

        # Should not find it for tenant 2
        config = repo.get(tenant_id_2, module, key)
        assert config is None

        # Should exist for tenant 1
        assert repo.exists(tenant_id_1, module, key) is True
        assert repo.exists(tenant_id_2, module, key) is False











