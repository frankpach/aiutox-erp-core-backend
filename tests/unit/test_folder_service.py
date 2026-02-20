"""Unit tests for FolderService - Permission methods."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.files.folder_service import FolderService
from app.models.folder import Folder, FolderPermission
from app.models.organization import Organization


class TestFolderServicePermissions:
    """Tests para métodos de permisos de FolderService."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_event_publisher(self):
        """Mock EventPublisher."""
        publisher = MagicMock()
        publisher.publish = AsyncMock(return_value="message-id-123")
        return publisher

    @pytest.fixture
    def mock_repository(self):
        """Mock FolderRepository."""
        repository = MagicMock()
        repository.get_by_id = MagicMock()
        repository.get_permissions = MagicMock(return_value=[])
        repository.create_permission = MagicMock()
        repository.delete_permission = MagicMock()
        return repository

    @pytest.fixture
    def service(self, mock_db_session, mock_event_publisher, mock_repository):
        """Fixture para crear instancia del servicio."""
        with patch("app.core.files.folder_service.FolderRepository", return_value=mock_repository):
            service = FolderService(mock_db_session, mock_event_publisher)
            service.repository = mock_repository
            return service

    @pytest.fixture
    def test_folder(self, test_user, test_tenant):
        """Fixture para crear una carpeta de prueba."""
        folder = Folder(
            id=uuid4(),
            name="Test Folder",
            tenant_id=test_tenant.id,
            created_by=test_user.id,
        )
        return folder

    def test_set_folder_permissions_user_success(self, service, mock_db_session, test_folder, test_user, test_tenant):
        """Test: Establecer permisos de carpeta para usuario exitosamente."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        permissions = [
            {
                "target_type": "user",
                "target_id": str(test_user.id),
                "can_view": True,
                "can_create_files": True,
                "can_edit": False,
                "can_delete": False,
            }
        ]

        # Mock repository methods
        service.repository.get_permissions.return_value = []
        mock_permission = FolderPermission(
            id=uuid4(),
            folder_id=folder_id,
            tenant_id=tenant_id,
            target_type="user",
            target_id=str(test_user.id),
            can_view=True,
            can_create_files=True,
            can_edit=False,
            can_delete=False,
        )
        service.repository.create_permission.return_value = mock_permission

        # Mock user query
        mock_db_session.query.return_value.filter.return_value.first.return_value = test_user

        # Act
        result = service.set_folder_permissions(
            folder_id=folder_id,
            permissions=permissions,
            tenant_id=tenant_id,
        )

        # Assert
        assert len(result) == 1
        assert result[0].target_type == "user"
        assert result[0].target_id == str(test_user.id)
        assert result[0].can_view is True
        service.repository.create_permission.assert_called_once()

    def test_set_folder_permissions_user_not_found(self, service, mock_db_session, test_folder, test_tenant):
        """Test: Establecer permisos con usuario no encontrado."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        permissions = [
            {
                "target_type": "user",
                "target_id": str(uuid4()),
                "can_view": True,
            }
        ]

        # Mock repository methods
        service.repository.get_permissions.return_value = []

        # Mock user query - user not found
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.set_folder_permissions(
                folder_id=folder_id,
                permissions=permissions,
                tenant_id=tenant_id,
            )

        assert "not found" in str(exc_info.value).lower()

    def test_set_folder_permissions_role_success(self, service, mock_db_session, test_folder, test_tenant):
        """Test: Establecer permisos de carpeta para rol exitosamente."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        # Use a valid global role instead of module role
        permissions = [
            {
                "target_type": "role",
                "target_id": "admin",  # Use global role that exists
                "can_view": True,
                "can_create_files": True,
            }
        ]

        # Mock repository methods
        service.repository.get_permissions.return_value = []
        mock_permission = FolderPermission(
            id=uuid4(),
            folder_id=folder_id,
            tenant_id=tenant_id,
            target_type="role",
            target_id="admin",
            can_view=True,
            can_create_files=True,
        )
        service.repository.create_permission.return_value = mock_permission

        # Mock ROLE_PERMISSIONS and MODULE_ROLES in the permissions module
        with patch("app.core.auth.permissions.ROLE_PERMISSIONS", {"admin": set()}):
            with patch("app.core.auth.permissions.MODULE_ROLES", {}):
                # Act
                result = service.set_folder_permissions(
                    folder_id=folder_id,
                    permissions=permissions,
                    tenant_id=tenant_id,
                )

                # Assert
                assert len(result) == 1
                assert result[0].target_type == "role"
                service.repository.create_permission.assert_called_once()

    def test_set_folder_permissions_organization_success(self, service, mock_db_session, test_folder, test_tenant):
        """Test: Establecer permisos de carpeta para organización exitosamente."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        org = Organization(
            id=uuid4(),
            name="Test Org",
            tenant_id=tenant_id,
        )
        permissions = [
            {
                "target_type": "organization",
                "target_id": str(org.id),
                "can_view": True,
            }
        ]

        # Mock repository methods
        service.repository.get_permissions.return_value = []
        mock_permission = FolderPermission(
            id=uuid4(),
            folder_id=folder_id,
            tenant_id=tenant_id,
            target_type="organization",
            target_id=str(org.id),
            can_view=True,
        )
        service.repository.create_permission.return_value = mock_permission

        # Mock organization query
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = org
        mock_db_session.query.return_value = mock_query

        # Act
        result = service.set_folder_permissions(
            folder_id=folder_id,
            permissions=permissions,
            tenant_id=tenant_id,
        )

        # Assert
        assert len(result) == 1
        assert result[0].target_type == "organization"
        service.repository.create_permission.assert_called_once()

    def test_set_folder_permissions_invalid_target_type(self, service, test_folder, test_tenant):
        """Test: Establecer permisos con tipo de target inválido."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        permissions = [
            {
                "target_type": "invalid",
                "target_id": str(uuid4()),
                "can_view": True,
            }
        ]

        # Mock repository methods
        service.repository.get_permissions.return_value = []

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.set_folder_permissions(
                folder_id=folder_id,
                permissions=permissions,
                tenant_id=tenant_id,
            )

        assert "Invalid target_type" in str(exc_info.value)

    def test_get_folder_permissions(self, service, test_folder, test_tenant):
        """Test: Obtener permisos de carpeta."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        mock_permissions = [
            FolderPermission(
                id=uuid4(),
                folder_id=folder_id,
                tenant_id=tenant_id,
                target_type="user",
                target_id=str(uuid4()),
                can_view=True,
            )
        ]
        service.repository.get_permissions.return_value = mock_permissions

        # Act
        result = service.get_folder_permissions(folder_id=folder_id, tenant_id=tenant_id)

        # Assert
        assert len(result) == 1
        assert result[0].target_type == "user"
        service.repository.get_permissions.assert_called_once_with(folder_id, tenant_id)

    def test_check_folder_permissions_owner_has_access(self, service, test_folder, test_user, test_tenant):
        """Test: Verificar que el propietario de la carpeta tiene acceso completo."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        user_id = test_folder.created_by  # Owner

        service.repository.get_by_id.return_value = test_folder
        service.repository.get_permissions.return_value = []

        # Act
        result = service.check_folder_permissions(
            folder_id=folder_id,
            user_id=user_id,
            tenant_id=tenant_id,
            permission="view",
        )

        # Assert
        assert result is True

    def test_check_folder_permissions_user_specific_permission(self, service, test_folder, test_user, test_tenant):
        """Test: Verificar permisos específicos de usuario."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        user_id = uuid4()  # Different user

        service.repository.get_by_id.return_value = test_folder
        mock_permission = FolderPermission(
            id=uuid4(),
            folder_id=folder_id,
            tenant_id=tenant_id,
            target_type="user",
            target_id=user_id,  # UUID, not string
            can_view=True,
            can_create_files=False,
        )
        service.repository.get_permissions.return_value = [mock_permission]

        # Act
        can_view = service.check_folder_permissions(
            folder_id=folder_id,
            user_id=user_id,
            tenant_id=tenant_id,
            permission="view",
        )
        can_create = service.check_folder_permissions(
            folder_id=folder_id,
            user_id=user_id,
            tenant_id=tenant_id,
            permission="create_files",
        )

        # Assert
        assert can_view is True
        assert can_create is False

    def test_check_folder_permissions_folder_not_found(self, service, test_tenant):
        """Test: Verificar permisos de carpeta no encontrada."""
        # Arrange
        folder_id = uuid4()
        tenant_id = test_tenant.id
        user_id = uuid4()

        service.repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            service.check_folder_permissions(
                folder_id=folder_id,
                user_id=user_id,
                tenant_id=tenant_id,
                permission="view",
            )

    def test_check_folder_permissions_invalid_permission(self, service, test_folder, test_user, test_tenant):
        """Test: Verificar permisos con permiso inválido."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        user_id = uuid4()  # Different user (not owner) to avoid early return

        # Make sure folder is not owned by test_user
        test_folder.created_by = uuid4()
        service.repository.get_by_id.return_value = test_folder
        service.repository.get_permissions.return_value = []  # No permissions

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            service.check_folder_permissions(
                folder_id=folder_id,
                user_id=user_id,
                tenant_id=tenant_id,
                permission="invalid_permission",
            )

        assert "Invalid permission" in str(exc_info.value)

    def test_check_inherited_permissions(self, service, test_folder, test_user, test_tenant):
        """Test: Verificar permisos heredados de carpetas padre."""
        # Arrange
        folder_id = test_folder.id
        tenant_id = test_tenant.id
        user_id = test_user.id

        # Create parent folder
        parent_folder = Folder(
            id=uuid4(),
            name="Parent Folder",
            tenant_id=tenant_id,
            created_by=uuid4(),
        )
        test_folder.parent_id = parent_folder.id
        test_folder.parent = parent_folder

        service.repository.get_by_id.return_value = test_folder

        # Mock parent permission - need to return permissions when called for parent folder
        parent_permission = FolderPermission(
            id=uuid4(),
            folder_id=parent_folder.id,
            tenant_id=tenant_id,
            target_type="user",
            target_id=user_id,  # UUID, not string
            can_view=True,
            can_create_files=True,
        )

        # Mock get_permissions to return parent permissions when called for parent folder
        def mock_get_permissions(f_id, t_id):
            if f_id == parent_folder.id:
                return [parent_permission]
            return []

        service.repository.get_permissions.side_effect = mock_get_permissions

        # Act
        result = service.check_inherited_permissions(
            folder_id=folder_id,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        # Assert
        assert result["can_view"] is True
        assert result["can_create_files"] is True

