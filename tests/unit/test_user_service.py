"""Unit tests for UserService."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


class TestUserService:
    """Test suite for UserService."""

    def test_create_user_success(self, db_session, test_tenant):
        """Test creating a user successfully."""
        service = UserService(db_session)

        user_data = UserCreate(
            email="newuser@example.com",
            password="password123",
            tenant_id=test_tenant.id,
            full_name="New User",
        )

        # Mock repository
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.email = user_data.email
        mock_user.full_name = user_data.full_name
        mock_user.is_active = True

        service.repository.get_by_email = Mock(return_value=None)
        service.repository.get_by_id = Mock(return_value=None)
        service.repository.create = Mock(return_value=mock_user)

        result = service.create_user(user_data)

        assert result["id"] == mock_user.id
        assert result["email"] == user_data.email
        assert result["full_name"] == user_data.full_name
        service.repository.get_by_email.assert_called_once_with(user_data.email)
        service.repository.create.assert_called_once()

    def test_create_user_duplicate_email(self, db_session, test_tenant):
        """Test creating a user with duplicate email raises error."""
        service = UserService(db_session)

        user_data = UserCreate(
            email="existing@example.com",
            password="password123",
            tenant_id=test_tenant.id,
        )

        # Mock existing user
        existing_user = Mock()
        service.repository.get_by_email = Mock(return_value=existing_user)

        with pytest.raises(ValueError, match="already exists"):
            service.create_user(user_data)

    def test_create_user_with_audit_log(self, db_session, test_tenant, test_user):
        """Test that audit log is created when created_by is provided."""
        service = UserService(db_session)

        user_data = UserCreate(
            email="newuser@example.com",
            password="password123",
            tenant_id=test_tenant.id,
        )

        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.email = user_data.email
        mock_user.full_name = None
        mock_user.is_active = True

        service.repository.get_by_email = Mock(return_value=None)
        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.create = Mock(return_value=mock_user)

        with patch("app.services.user_service.log_user_action") as mock_log, patch(
            "app.services.user_service.create_audit_log_entry"
        ) as mock_audit:
            service.create_user(
                user_data,
                created_by=test_user.id,
                ip_address="127.0.0.1",
                user_agent="test-agent",
            )

            mock_log.assert_called_once()
            mock_audit.assert_called_once()

    def test_get_user_success(self, db_session, test_user):
        """Test getting a user by ID."""
        service = UserService(db_session)

        service.repository.get_by_id = Mock(return_value=test_user)

        result = service.get_user(test_user.id)

        assert result is not None
        assert result["id"] == test_user.id
        assert result["email"] == test_user.email
        service.repository.get_by_id.assert_called_once_with(test_user.id)

    def test_get_user_not_found(self, db_session):
        """Test getting a non-existent user."""
        service = UserService(db_session)
        non_existent_id = uuid4()

        service.repository.get_by_id = Mock(return_value=None)

        result = service.get_user(non_existent_id)

        assert result is None

    def test_get_user_by_email(self, db_session, test_user):
        """Test getting a user by email."""
        service = UserService(db_session)

        service.repository.get_by_email = Mock(return_value=test_user)

        result = service.get_user_by_email(test_user.email)

        assert result is not None
        assert result["email"] == test_user.email
        service.repository.get_by_email.assert_called_once_with(test_user.email)

    def test_update_user_success(self, db_session, test_user):
        """Test updating a user successfully."""
        service = UserService(db_session)

        update_data = UserUpdate(full_name="Updated Name", is_active=False)

        updated_user = Mock()
        updated_user.id = test_user.id
        updated_user.email = test_user.email
        updated_user.full_name = "Updated Name"
        updated_user.is_active = False
        updated_user.created_at = test_user.created_at
        updated_user.updated_at = test_user.updated_at

        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.update = Mock(return_value=updated_user)

        result = service.update_user(test_user.id, update_data)

        assert result is not None
        assert result["full_name"] == "Updated Name"
        assert result["is_active"] is False
        service.repository.get_by_id.assert_called_with(test_user.id)
        service.repository.update.assert_called_once()

    def test_update_user_not_found(self, db_session):
        """Test updating a non-existent user."""
        service = UserService(db_session)
        non_existent_id = uuid4()
        update_data = UserUpdate(full_name="New Name")

        service.repository.get_by_id = Mock(return_value=None)

        result = service.update_user(non_existent_id, update_data)

        assert result is None

    def test_update_user_duplicate_email(self, db_session, test_user):
        """Test updating user email to an existing email raises error."""
        service = UserService(db_session)

        # Create another user
        other_user = Mock()
        other_user.id = uuid4()
        other_user.email = "other@example.com"

        update_data = UserUpdate(email="other@example.com")

        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.get_by_email = Mock(return_value=other_user)

        with pytest.raises(ValueError, match="already exists"):
            service.update_user(test_user.id, update_data)

    def test_delete_user_success(self, db_session, test_user):
        """Test soft deleting a user."""
        service = UserService(db_session)

        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.update = Mock(return_value=test_user)

        result = service.delete_user(test_user.id)

        assert result is True
        assert test_user.is_active is False
        service.repository.get_by_id.assert_called_once_with(test_user.id)
        service.repository.update.assert_called_once()

    def test_delete_user_not_found(self, db_session):
        """Test deleting a non-existent user."""
        service = UserService(db_session)
        non_existent_id = uuid4()

        service.repository.get_by_id = Mock(return_value=None)

        result = service.delete_user(non_existent_id)

        assert result is False

    def test_list_users_with_pagination(self, db_session, test_tenant):
        """Test listing users with pagination."""
        service = UserService(db_session)

        # Mock users
        mock_users = []
        for i in range(3):
            user = Mock()
            user.id = uuid4()
            user.email = f"user{i}@example.com"
            user.full_name = f"User {i}"
            user.is_active = True
            user.created_at = test_tenant.created_at
            user.updated_at = test_tenant.created_at
            mock_users.append(user)

        service.repository.get_all_by_tenant = Mock(return_value=mock_users)
        service.repository.db.query = Mock()
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.count = Mock(return_value=10)
        service.repository.db.query.return_value = mock_query

        users, total = service.list_users(test_tenant.id, skip=0, limit=10)

        assert len(users) == 3
        assert total == 10
        assert all("id" in user for user in users)
        assert all("email" in user for user in users)





