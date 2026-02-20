"""Unit tests for StorageConfigService."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import APIException
from app.core.files.storage_config_service import StorageConfigService


class TestStorageConfigService:
    """Tests para StorageConfigService."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_config_service(self):
        """Mock ConfigService."""
        config_service = MagicMock()
        config_service.get = MagicMock(return_value="default")
        config_service.set = MagicMock()
        return config_service

    @pytest.fixture
    def service(self, mock_db_session, mock_config_service):
        """Fixture para crear instancia del servicio."""
        with patch(
            "app.core.files.storage_config_service.ConfigService",
            return_value=mock_config_service,
        ):
            service = StorageConfigService(mock_db_session)
            service.config_service = mock_config_service
            return service

    def test_get_storage_config_default_local(self, service, mock_config_service):
        """Test: Obtener configuración de almacenamiento por defecto (local)."""
        # Arrange
        tenant_id = uuid4()
        mock_config_service.get.side_effect = lambda tid, mod, key, default: {
            "storage.backend": "local",
            "storage.local.base_path": "./storage",
        }.get(key, default)

        # Act
        config = service.get_storage_config(tenant_id)

        # Assert
        assert config["backend"] == "local"
        assert "local" in config
        assert config["local"]["base_path"] == "./storage"

    def test_get_storage_config_s3(self, service, mock_config_service):
        """Test: Obtener configuración de almacenamiento S3."""
        # Arrange
        tenant_id = uuid4()
        mock_config_service.get.side_effect = lambda tid, mod, key, default: {
            "storage.backend": "s3",
            "storage.s3.bucket_name": "test-bucket",
            "storage.s3.access_key_id": "test-key",
            "storage.s3.region": "us-east-1",
        }.get(key, default)

        # Act
        config = service.get_storage_config(tenant_id)

        # Assert
        assert config["backend"] == "s3"
        assert "s3" in config
        assert config["s3"]["bucket_name"] == "test-bucket"
        assert config["s3"]["access_key_id"] == "test-key"
        assert config["s3"]["secret_access_key"] == "***"  # Never returned
        assert config["s3"]["region"] == "us-east-1"

    def test_update_storage_config_local_success(self, service, mock_config_service):
        """Test: Actualizar configuración de almacenamiento local exitosamente."""
        # Arrange
        tenant_id = uuid4()
        user_id = uuid4()
        config = {
            "backend": "local",
            "local": {
                "base_path": "/custom/storage",
            },
        }

        # Mock get_storage_config to return updated config
        def mock_get(tid, mod, key, default):
            if key == "storage.backend":
                return "local"
            elif key == "storage.local.base_path":
                return "/custom/storage"
            return default

        mock_config_service.get.side_effect = mock_get

        # Act
        result = service.update_storage_config(
            tenant_id=tenant_id,
            config=config,
            user_id=user_id,
        )

        # Assert
        assert result["backend"] == "local"
        assert result["local"]["base_path"] == "/custom/storage"
        assert mock_config_service.set.called

    def test_update_storage_config_invalid_backend(self, service):
        """Test: Actualizar configuración con backend inválido."""
        # Arrange
        tenant_id = uuid4()
        config = {"backend": "invalid"}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_storage_config(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_BACKEND"

    def test_update_storage_config_s3_missing_bucket_name(self, service):
        """Test: Actualizar configuración S3 sin nombre de bucket."""
        # Arrange
        tenant_id = uuid4()
        config = {
            "backend": "s3",
            "s3": {
                "access_key_id": "test-key",
                "secret_access_key": "test-secret",
                "region": "us-east-1",
            },
        }

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_storage_config(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "MISSING_BUCKET_NAME"

    def test_update_storage_config_s3_invalid_bucket_name(self, service):
        """Test: Actualizar configuración S3 con nombre de bucket inválido."""
        # Arrange
        tenant_id = uuid4()
        config = {
            "backend": "s3",
            "s3": {
                "bucket_name": "AB",  # Too short
                "access_key_id": "test-key",
                "secret_access_key": "test-secret",
                "region": "us-east-1",
            },
        }

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_storage_config(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_BUCKET_NAME"

    def test_update_storage_config_s3_invalid_region(self, service):
        """Test: Actualizar configuración S3 con región inválida."""
        # Arrange
        tenant_id = uuid4()
        config = {
            "backend": "s3",
            "s3": {
                "bucket_name": "test-bucket",
                "access_key_id": "test-key",
                "secret_access_key": "test-secret",
                "region": "invalid-region",
            },
        }

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_storage_config(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_AWS_REGION"

    def test_update_storage_config_s3_missing_credentials(self, service):
        """Test: Actualizar configuración S3 sin credenciales."""
        # Arrange
        tenant_id = uuid4()
        config = {
            "backend": "s3",
            "s3": {
                "bucket_name": "test-bucket",
                "region": "us-east-1",
            },
        }

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_storage_config(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "MISSING_CREDENTIALS"

    def test_update_file_limits_invalid_max_file_size(self, service):
        """Test: Actualizar límites con tamaño máximo inválido."""
        # Arrange
        tenant_id = uuid4()
        limits = {"max_file_size": -1}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_file_limits(tenant_id=tenant_id, limits=limits)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_MAX_FILE_SIZE"

    def test_update_file_limits_invalid_mime_type_format(self, service):
        """Test: Actualizar límites con formato de MIME type inválido."""
        # Arrange
        tenant_id = uuid4()
        limits = {"allowed_mime_types": ["invalid-mime-type"]}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_file_limits(tenant_id=tenant_id, limits=limits)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_MIME_TYPE_FORMAT"

    def test_update_file_limits_invalid_max_versions(self, service):
        """Test: Actualizar límites con máximo de versiones inválido."""
        # Arrange
        tenant_id = uuid4()
        limits = {"max_versions_per_file": 0}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_file_limits(tenant_id=tenant_id, limits=limits)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_MAX_VERSIONS"

    def test_update_file_limits_invalid_retention_days(self, service):
        """Test: Actualizar límites con días de retención inválidos."""
        # Arrange
        tenant_id = uuid4()
        limits = {"retention_days": -1}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_file_limits(tenant_id=tenant_id, limits=limits)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_RETENTION_DAYS"

    def test_update_thumbnail_config_invalid_width(self, service):
        """Test: Actualizar configuración de thumbnails con ancho inválido."""
        # Arrange
        tenant_id = uuid4()
        config = {"default_width": 0}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_thumbnail_config(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_WIDTH"

    def test_update_thumbnail_config_invalid_quality(self, service):
        """Test: Actualizar configuración de thumbnails con calidad inválida."""
        # Arrange
        tenant_id = uuid4()
        config = {"quality": 101}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            service.update_thumbnail_config(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "INVALID_QUALITY"

    @pytest.mark.asyncio
    async def test_test_s3_connection_missing_credentials(self, service):
        """Test: Probar conexión S3 sin credenciales."""
        # Arrange
        tenant_id = uuid4()
        config = {"bucket_name": "test-bucket"}

        # Act & Assert
        with pytest.raises(APIException) as exc_info:
            await service.test_s3_connection(tenant_id=tenant_id, config=config)

        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "MISSING_CREDENTIALS"

    def test_get_storage_stats(self, service, mock_db_session):
        """Test: Obtener estadísticas de almacenamiento."""
        # Arrange
        tenant_id = uuid4()

        # Mock query results
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 1000  # total_size
        mock_query.count.return_value = 5  # total_files
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [("image/png", 3), ("application/pdf", 2)]

        mock_db_session.query.return_value = mock_query

        # Act
        stats = service.get_storage_stats(tenant_id)

        # Assert
        assert "total_space_used" in stats
        assert "total_files" in stats
        assert "total_folders" in stats
        assert "mime_distribution" in stats
