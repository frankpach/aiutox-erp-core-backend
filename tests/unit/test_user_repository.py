"""Unit tests for UserRepository."""

from uuid import uuid4

import pytest

from app.core.auth.password import hash_password
from app.repositories.user_repository import UserRepository


class TestUserRepository:
    """Test suite for UserRepository."""

    def test_create_user(self, db_session, test_tenant):
        """Test creating a user in the database."""
        repo = UserRepository(db_session)
        user_data = {
            "email": f"test-{uuid4().hex[:8]}@example.com",
            "password_hash": hash_password("test_password_123"),
            "full_name": "Test User",
            "tenant_id": test_tenant.id,
            "is_active": True,
        }
        user = repo.create(user_data)

        assert user.email == user_data["email"]
        assert user.id is not None
        assert user.tenant_id == test_tenant.id
        assert user.is_active is True

    def test_get_by_id(self, db_session, test_user):
        """Test getting a user by ID."""
        repo = UserRepository(db_session)
        user = repo.get_by_id(test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    def test_get_by_id_not_found(self, db_session):
        """Test getting a user by non-existent ID."""
        repo = UserRepository(db_session)
        non_existent_id = uuid4()
        user = repo.get_by_id(non_existent_id)

        assert user is None

    def test_get_by_email(self, db_session, test_user):
        """Test getting a user by email."""
        repo = UserRepository(db_session)
        user = repo.get_by_email(test_user.email)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    def test_get_by_email_not_found(self, db_session):
        """Test getting a user by non-existent email."""
        repo = UserRepository(db_session)
        user = repo.get_by_email("nonexistent@example.com")

        assert user is None

    def test_get_by_email_and_tenant(self, db_session, test_user, test_tenant):
        """Test getting a user by email and tenant ID."""
        repo = UserRepository(db_session)
        user = repo.get_by_email_and_tenant(test_user.email, test_tenant.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email
        assert user.tenant_id == test_tenant.id

    def test_get_by_email_and_tenant_wrong_tenant(self, db_session, test_user):
        """Test getting a user by email with wrong tenant ID."""
        repo = UserRepository(db_session)
        wrong_tenant_id = uuid4()
        user = repo.get_by_email_and_tenant(test_user.email, wrong_tenant_id)

        assert user is None

    def test_get_all_pagination(self, db_session, test_tenant):
        """Test getting all users with pagination."""
        repo = UserRepository(db_session)

        # Create multiple users
        for i in range(5):
            user_data = {
                "email": f"user{i}-{uuid4().hex[:8]}@example.com",
                "password_hash": hash_password("password"),
                "full_name": f"User {i}",
                "tenant_id": test_tenant.id,
                "is_active": True,
            }
            repo.create(user_data)

        # Test pagination
        users_page1 = repo.get_all(skip=0, limit=2)
        assert len(users_page1) == 2

        users_page2 = repo.get_all(skip=2, limit=2)
        assert len(users_page2) == 2

    def test_get_all_by_tenant(self, db_session, test_tenant):
        """Test getting all users filtered by tenant."""
        repo = UserRepository(db_session)

        # Create users for this tenant
        for i in range(3):
            user_data = {
                "email": f"tenant-user{i}-{uuid4().hex[:8]}@example.com",
                "password_hash": hash_password("password"),
                "full_name": f"Tenant User {i}",
                "tenant_id": test_tenant.id,
                "is_active": True,
            }
            repo.create(user_data)

        # Create user for different tenant
        from app.models.tenant import Tenant

        other_tenant = Tenant(name="Other Tenant", slug=f"other-{uuid4().hex[:8]}")
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_user_data = {
            "email": f"other-{uuid4().hex[:8]}@example.com",
            "password_hash": hash_password("password"),
            "full_name": "Other Tenant User",
            "tenant_id": other_tenant.id,
            "is_active": True,
        }
        repo.create(other_user_data)

        # Get users for test_tenant
        tenant_users = repo.get_all_by_tenant(test_tenant.id)
        assert len(tenant_users) >= 3
        assert all(user.tenant_id == test_tenant.id for user in tenant_users)

    def test_verify_password_correct(self, db_session, test_user):
        """Test verifying a correct password."""
        repo = UserRepository(db_session)
        plain_password = getattr(test_user, "_plain_password", "test_password_123")
        result = repo.verify_password(test_user, plain_password)

        assert result is True

    def test_verify_password_incorrect(self, db_session, test_user):
        """Test verifying an incorrect password."""
        repo = UserRepository(db_session)
        result = repo.verify_password(test_user, "wrong_password")

        assert result is False

    def test_update_user(self, db_session, test_user):
        """Test updating user data."""
        repo = UserRepository(db_session)
        update_data = {
            "full_name": "Updated Name",
            "is_active": False,
        }
        updated_user = repo.update(test_user, update_data)

        assert updated_user.full_name == "Updated Name"
        assert updated_user.is_active is False
        assert updated_user.id == test_user.id

    def test_update_user_partial(self, db_session, test_user):
        """Test updating user with partial data (None values should be ignored)."""
        repo = UserRepository(db_session)
        original_email = test_user.email
        update_data = {
            "full_name": "New Name",
            "email": None,  # Should be ignored
        }
        updated_user = repo.update(test_user, update_data)

        assert updated_user.full_name == "New Name"
        assert updated_user.email == original_email  # Should not change

    def test_delete_user(self, db_session, test_user):
        """Test deleting a user."""
        repo = UserRepository(db_session)
        user_id = test_user.id

        repo.delete(test_user)

        # Verify user is deleted
        deleted_user = repo.get_by_id(user_id)
        assert deleted_user is None






