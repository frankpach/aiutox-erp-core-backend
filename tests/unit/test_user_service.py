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

        # Mock refresh token repository
        with patch("app.repositories.refresh_token_repository.RefreshTokenRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.revoke_all_user_tokens = Mock(return_value=2)
            mock_repo_class.return_value = mock_repo

            result = service.update_user(test_user.id, update_data)

            assert result is not None
            assert result["full_name"] == "Updated Name"
            assert result["is_active"] is False
            service.repository.get_by_id.assert_called_with(test_user.id)
            service.repository.update.assert_called_once()
            # Verify tokens are revoked when is_active changes to False
            mock_repo.revoke_all_user_tokens.assert_called_once_with(test_user.id)

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

    def test_update_user_is_active_true_no_token_revocation(self, db_session, test_user):
        """Test that updating is_active to True does not revoke tokens."""
        service = UserService(db_session)

        # Set user as inactive initially
        test_user.is_active = False
        update_data = UserUpdate(is_active=True)

        updated_user = Mock()
        updated_user.id = test_user.id
        updated_user.email = test_user.email
        updated_user.full_name = test_user.full_name
        updated_user.is_active = True
        updated_user.created_at = test_user.created_at
        updated_user.updated_at = test_user.updated_at

        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.update = Mock(return_value=updated_user)

        # Mock refresh token repository
        with patch("app.repositories.refresh_token_repository.RefreshTokenRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.revoke_all_user_tokens = Mock(return_value=0)
            mock_repo_class.return_value = mock_repo

            result = service.update_user(test_user.id, update_data)

            assert result is not None
            assert result["is_active"] is True
            # Verify tokens are NOT revoked when activating user
            mock_repo.revoke_all_user_tokens.assert_not_called()

    def test_delete_user_success(self, db_session, test_user):
        """Test hard deleting a user."""
        service = UserService(db_session)

        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.delete = Mock()

        result = service.delete_user(test_user.id)

        assert result is True
        service.repository.get_by_id.assert_called_once_with(test_user.id)
        service.repository.delete.assert_called_once_with(test_user)

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

        service.repository.get_all_by_tenant = Mock(return_value=(mock_users, 10))

        users, total = service.list_users(test_tenant.id, skip=0, limit=10)

        assert len(users) == 3
        assert total == 10
        assert all("id" in user for user in users)
        assert all("email" in user for user in users)

    def test_list_users_with_filters(self, db_session, test_tenant):
        """Test listing users with filters."""
        service = UserService(db_session)

        # Mock users
        mock_users = []
        for i in range(2):
            user = Mock()
            user.id = uuid4()
            user.email = f"user{i}@example.com"
            user.full_name = f"User {i}"
            user.is_active = True
            user.created_at = test_tenant.created_at
            user.updated_at = test_tenant.created_at
            mock_users.append(user)

        service.repository.get_all_by_tenant = Mock(return_value=(mock_users, 2))

        # Test with search filter
        users, total = service.list_users(
            test_tenant.id, skip=0, limit=10, filters={"search": "user"}
        )
        assert len(users) == 2
        service.repository.get_all_by_tenant.assert_called_with(
            tenant_id=test_tenant.id, skip=0, limit=10, filters={"search": "user"}
        )

        # Test with is_active filter
        users, total = service.list_users(
            test_tenant.id, skip=0, limit=10, filters={"is_active": True}
        )
        assert len(users) == 2
        service.repository.get_all_by_tenant.assert_called_with(
            tenant_id=test_tenant.id, skip=0, limit=10, filters={"is_active": True}
        )

    def test_deactivate_user_success(self, db_session, test_user):
        """Test deactivating a user (soft delete with token revocation)."""
        service = UserService(db_session)

        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.update = Mock(return_value=test_user)

        # Mock refresh token repository
        with patch("app.repositories.refresh_token_repository.RefreshTokenRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.revoke_all_user_tokens = Mock(return_value=2)
            mock_repo_class.return_value = mock_repo

            result = service.deactivate_user(test_user.id)

            assert result is True
            assert test_user.is_active is False
            service.repository.get_by_id.assert_called_once_with(test_user.id)
            service.repository.update.assert_called_once()
            mock_repo.revoke_all_user_tokens.assert_called_once_with(test_user.id)

    def test_delete_user_hard_delete(self, db_session, test_user):
        """Test hard deleting a user."""
        service = UserService(db_session)

        service.repository.get_by_id = Mock(return_value=test_user)
        service.repository.delete = Mock()

        result = service.delete_user(test_user.id)

        assert result is True
        service.repository.get_by_id.assert_called_once_with(test_user.id)
        service.repository.delete.assert_called_once_with(test_user)

    def test_bulk_action_activate(self, db_session, test_tenant, test_user):
        """Test bulk activate action."""
        service = UserService(db_session)

        # Create test users
        user1 = Mock()
        user1.id = uuid4()
        user1.tenant_id = test_tenant.id
        user1.email = "user1@example.com"
        user1.is_active = False

        user2 = Mock()
        user2.id = uuid4()
        user2.tenant_id = test_tenant.id
        user2.email = "user2@example.com"
        user2.is_active = False

        service.repository.get_by_id = Mock(side_effect=[user1, user2])
        service.repository.update = Mock(side_effect=[user1, user2])

        with patch("app.services.user_service.log_user_action"), patch(
            "app.services.user_service.create_audit_log_entry"
        ):
            result = service.bulk_action(
                user_ids=[user1.id, user2.id],
                action="activate",
                tenant_id=test_tenant.id,
                performed_by=test_user.id,
            )

        assert result["success"] == 2
        assert result["failed"] == 0
        assert service.repository.update.call_count == 2

    def test_bulk_action_deactivate(self, db_session, test_tenant, test_user):
        """Test bulk deactivate action (soft delete with token revocation)."""
        service = UserService(db_session)

        user1 = Mock()
        user1.id = uuid4()
        user1.tenant_id = test_tenant.id
        user1.email = "user1@example.com"
        user1.is_active = True

        service.repository.get_by_id = Mock(return_value=user1)
        service.repository.update = Mock(return_value=user1)

        # Mock refresh token repository
        with patch("app.repositories.refresh_token_repository.RefreshTokenRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.revoke_all_user_tokens = Mock(return_value=2)
            mock_repo_class.return_value = mock_repo

            with patch("app.services.user_service.log_user_action"), patch(
                "app.services.user_service.create_audit_log_entry"
            ):
                result = service.bulk_action(
                    user_ids=[user1.id],
                    action="deactivate",
                    tenant_id=test_tenant.id,
                    performed_by=test_user.id,
                )

            assert result["success"] == 1
            assert result["failed"] == 0
            service.repository.update.assert_called_once()
            mock_repo.revoke_all_user_tokens.assert_called_once_with(user1.id)

    def test_bulk_action_delete(self, db_session, test_tenant, test_user):
        """Test bulk delete action (soft delete with token revocation)."""
        service = UserService(db_session)

        user1 = Mock()
        user1.id = uuid4()
        user1.tenant_id = test_tenant.id
        user1.email = "user1@example.com"
        user1.is_active = True

        service.repository.get_by_id = Mock(return_value=user1)
        service.repository.update = Mock(return_value=user1)

        # Mock refresh token repository
        with patch("app.repositories.refresh_token_repository.RefreshTokenRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo.revoke_all_user_tokens = Mock(return_value=2)
            mock_repo_class.return_value = mock_repo

            with patch("app.services.user_service.log_user_action"), patch(
                "app.services.user_service.create_audit_log_entry"
            ):
                result = service.bulk_action(
                    user_ids=[user1.id],
                    action="delete",
                    tenant_id=test_tenant.id,
                    performed_by=test_user.id,
                )

            assert result["success"] == 1
            assert result["failed"] == 0
            service.repository.update.assert_called_once()
            mock_repo.revoke_all_user_tokens.assert_called_once_with(user1.id)

    def test_bulk_action_tenant_mismatch(self, db_session, test_tenant, test_user):
        """Test bulk action fails for users from different tenant."""
        service = UserService(db_session)

        user1 = Mock()
        user1.id = uuid4()
        user1.tenant_id = uuid4()  # Different tenant
        user1.email = "user1@example.com"

        service.repository.get_by_id = Mock(return_value=user1)

        result = service.bulk_action(
            user_ids=[user1.id],
            action="activate",
            tenant_id=test_tenant.id,
            performed_by=test_user.id,
        )

        assert result["success"] == 0
        assert result["failed"] == 1
        assert str(user1.id) in result["failed_ids"]

    def test_bulk_action_invalid_action(self, db_session, test_tenant, test_user):
        """Test bulk action with invalid action type."""
        service = UserService(db_session)

        user1 = Mock()
        user1.id = uuid4()
        user1.tenant_id = test_tenant.id

        service.repository.get_by_id = Mock(return_value=user1)

        result = service.bulk_action(
            user_ids=[user1.id],
            action="invalid_action",
            tenant_id=test_tenant.id,
            performed_by=test_user.id,
        )

        assert result["success"] == 0
        assert result["failed"] == 1













