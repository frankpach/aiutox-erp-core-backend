"""Unit tests for PermissionService."""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import APIException
from app.services.permission_service import PermissionService


class TestPermissionService:
    """Test suite for PermissionService."""

    def test_get_user_global_roles(self, db_session, test_user):
        """Test getting global roles for a user."""
        service = PermissionService(db_session)

        from app.models.user_role import UserRole

        # Mock query result
        mock_role = Mock(spec=UserRole)
        mock_role.role = "admin"
        service.db.query = Mock()
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[mock_role])
        service.db.query.return_value = mock_query

        roles = service.get_user_global_roles(test_user.id)

        assert "admin" in roles
        assert len(roles) == 1

    def test_get_role_permissions(self, db_session):
        """Test getting permissions for a specific role."""
        service = PermissionService(db_session)

        permissions = service.get_role_permissions("admin")

        assert isinstance(permissions, set)
        assert len(permissions) > 0

    def test_get_role_permissions_invalid_role(self, db_session):
        """Test getting permissions for an invalid role returns empty set."""
        service = PermissionService(db_session)

        permissions = service.get_role_permissions("invalid_role")

        assert permissions == set()

    def test_get_user_module_roles(self, db_session, test_user):
        """Test getting module roles for a user."""
        service = PermissionService(db_session)

        from app.models.module_role import ModuleRole

        # Mock query result
        mock_module_role = Mock(spec=ModuleRole)
        mock_module_role.module = "inventory"
        mock_module_role.role_name = "editor"
        service.db.query = Mock()
        mock_query = Mock()
        mock_query.filter = Mock(return_value=mock_query)
        mock_query.all = Mock(return_value=[mock_module_role])
        service.db.query.return_value = mock_query

        module_roles = service.get_user_module_roles(test_user.id)

        assert len(module_roles) == 1
        assert module_roles[0].module == "inventory"

    def test_get_module_role_permissions(self, db_session):
        """Test getting permissions for a module role."""
        service = PermissionService(db_session)

        permissions = service.get_module_role_permissions("inventory", "editor")

        assert isinstance(permissions, set)

    def test_get_effective_permissions(self, db_session, test_user):
        """Test getting effective permissions combining all sources."""
        service = PermissionService(db_session)

        # Mock global roles
        with patch.object(service, "get_user_global_roles", return_value=["admin"]):
            with patch.object(
                service, "get_role_permissions", return_value={"auth.manage_users"}
            ):
                with patch.object(service, "get_user_module_roles", return_value=[]):
                    with patch.object(
                        service, "get_user_delegated_permissions", return_value=[]
                    ):
                        permissions = service.get_effective_permissions(test_user.id)

                        assert "auth.manage_users" in permissions

    def test_grant_permission_success(self, db_session, test_user):
        """Test granting a permission successfully."""
        service = PermissionService(db_session)

        # Mock effective permissions (granter has permission)
        with patch.object(
            service,
            "get_effective_permissions",
            return_value={"inventory.manage_users"},
        ):
            # Mock repository
            from app.models.delegated_permission import DelegatedPermission

            mock_permission = Mock(spec=DelegatedPermission)
            mock_permission.id = uuid4()
            mock_permission.user_id = test_user.id
            mock_permission.granted_by = test_user.id
            mock_permission.module = "inventory"
            mock_permission.permission = "inventory.edit"

            with patch(
                "app.services.permission_service.PermissionRepository"
            ) as mock_repo_class:
                mock_repo = Mock()
                mock_repo.create_delegated_permission = Mock(
                    return_value=mock_permission
                )
                mock_repo_class.return_value = mock_repo

                with (
                    patch("app.services.permission_service.log_permission_change"),
                    patch("app.services.permission_service.create_audit_log_entry"),
                    patch(
                        "app.repositories.user_repository.UserRepository"
                    ) as mock_user_repo_class,
                ):
                    mock_user_repo = Mock()
                    mock_user = Mock()
                    mock_user.tenant_id = uuid4()
                    mock_user_repo.get_by_id = Mock(return_value=mock_user)
                    mock_user_repo_class.return_value = mock_user_repo

                    result = service.grant_permission(
                        user_id=test_user.id,
                        module="inventory",
                        permission="inventory.edit",
                        expires_at=None,
                        granted_by=test_user.id,
                    )

                    assert result.id == mock_permission.id
                    assert result.permission == "inventory.edit"

    def test_grant_permission_insufficient_permissions(self, db_session, test_user):
        """Test granting permission when granter lacks required permission."""
        service = PermissionService(db_session)

        # Mock effective permissions (granter does NOT have permission)
        with patch.object(service, "get_effective_permissions", return_value=set()):
            with pytest.raises(APIException) as exc_info:
                service.grant_permission(
                    user_id=test_user.id,
                    module="inventory",
                    permission="inventory.edit",
                    expires_at=None,
                    granted_by=test_user.id,
                )

            assert exc_info.value.status_code == 403
            assert "PERMISSION_DENIED" in exc_info.value.code

    def test_grant_permission_invalid_manage_users(self, db_session, test_user):
        """Test that *.manage_users cannot be delegated."""
        service = PermissionService(db_session)

        with patch.object(
            service,
            "get_effective_permissions",
            return_value={"inventory.manage_users"},
        ):
            with pytest.raises(APIException) as exc_info:
                service.grant_permission(
                    user_id=test_user.id,
                    module="inventory",
                    permission="inventory.manage_users",
                    expires_at=None,
                    granted_by=test_user.id,
                )

            assert exc_info.value.status_code == 400
            assert "INVALID_PERMISSION" in exc_info.value.code

    def test_grant_permission_invalid_global_permission(self, db_session, test_user):
        """Test that global permissions (auth.*, system.*) cannot be delegated."""
        service = PermissionService(db_session)

        with patch.object(
            service, "get_effective_permissions", return_value={"auth.manage_users"}
        ):
            with pytest.raises(APIException) as exc_info:
                service.grant_permission(
                    user_id=test_user.id,
                    module="auth",
                    permission="auth.manage_users",
                    expires_at=None,
                    granted_by=test_user.id,
                )

            assert exc_info.value.status_code == 400
            assert "INVALID_PERMISSION" in exc_info.value.code

    def test_revoke_permission_success(self, db_session, test_user):
        """Test revoking a permission successfully."""
        service = PermissionService(db_session)

        permission_id = uuid4()

        with patch(
            "app.services.permission_service.PermissionRepository"
        ) as mock_repo_class:
            mock_repo = Mock()
            mock_permission = Mock()
            mock_permission.id = permission_id
            mock_permission.revoked_at = None
            mock_repo.get_delegated_permission_by_id = Mock(
                return_value=mock_permission
            )
            mock_repo.revoke_permission = Mock(return_value=True)
            mock_repo_class.return_value = mock_repo

            with patch.object(
                service, "get_effective_permissions", return_value={"auth.manage_users"}
            ):
                with (
                    patch("app.services.permission_service.log_permission_change"),
                    patch("app.services.permission_service.create_audit_log_entry"),
                    patch(
                        "app.repositories.user_repository.UserRepository"
                    ) as mock_user_repo_class,
                ):
                    mock_user_repo = Mock()
                    mock_user = Mock()
                    mock_user.tenant_id = uuid4()
                    mock_user_repo.get_by_id = Mock(return_value=mock_user)
                    mock_user_repo_class.return_value = mock_user_repo

                    # revoke_permission no retorna nada, solo lanza excepciones si hay error
                    service.revoke_permission(permission_id, test_user.id)

                    mock_repo.revoke_permission.assert_called_once()

    def test_revoke_all_user_permissions(self, db_session, test_user):
        """Test revoking all permissions for a user."""
        service = PermissionService(db_session)

        with patch.object(
            service, "get_effective_permissions", return_value={"auth.manage_users"}
        ):
            with patch.object(service, "get_user_global_roles", return_value=[]):
                with patch.object(
                    service, "get_user_delegated_permissions", return_value=[]
                ):
                    with patch(
                        "app.services.permission_service.PermissionRepository"
                    ) as mock_repo_class:
                        mock_repo = Mock()
                        mock_repo.revoke_all_user_permissions = Mock(return_value=3)
                        mock_repo_class.return_value = mock_repo

                        with (
                            patch(
                                "app.services.permission_service.log_permission_change"
                            ),
                            patch(
                                "app.services.permission_service.create_audit_log_entry"
                            ),
                            patch(
                                "app.repositories.user_repository.UserRepository"
                            ) as mock_user_repo_class,
                        ):
                            mock_user_repo = Mock()
                            mock_user = Mock()
                            mock_user.tenant_id = uuid4()
                            mock_user_repo.get_by_id = Mock(return_value=mock_user)
                            mock_user_repo_class.return_value = mock_user_repo

                            count = service.revoke_all_user_permissions(
                                test_user.id, test_user.id
                            )

                            assert count == 3
                            mock_repo.revoke_all_user_permissions.assert_called_once_with(
                                test_user.id, test_user.id
                            )
