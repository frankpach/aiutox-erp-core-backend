"""Unit tests for FileService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.core.files.service import FileService
from app.core.files.storage import LocalStorageBackend
from app.core.pubsub import EventPublisher
from app.models.file import StorageBackend


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def mock_storage_backend():
    """Create a mock storage backend."""
    backend = MagicMock(spec=LocalStorageBackend)
    backend.upload = AsyncMock(return_value="test/path/file.pdf")
    # download should return the same content that was uploaded
    backend.download = AsyncMock(return_value=b"test file content")
    backend.delete = AsyncMock(return_value=True)
    backend.exists = AsyncMock(return_value=True)
    backend.get_url = AsyncMock(return_value="/files/test/path/file.pdf")
    return backend


@pytest.fixture
def file_service(db_session, mock_storage_backend, mock_event_publisher):
    """Create FileService instance."""
    return FileService(
        db=db_session,
        storage_backend=mock_storage_backend,
        event_publisher=mock_event_publisher,
    )


@pytest.mark.asyncio
async def test_upload_file(
    file_service, test_user, test_tenant, mock_storage_backend, mock_event_publisher
):
    """Test uploading a file."""
    file_content = b"test file content"
    filename = "test.pdf"

    file = await file_service.upload_file(
        file_content=file_content,
        filename=filename,
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert file.name == filename
    assert file.original_name == filename
    assert file.size == len(file_content)
    assert file.tenant_id == test_tenant.id
    assert file.uploaded_by == test_user.id
    assert file.is_current is True

    # Verify storage backend was called
    mock_storage_backend.upload.assert_called_once()

    # Verify event was published
    assert mock_event_publisher.publish.called
    call_args = mock_event_publisher.publish.call_args
    assert call_args[1]["event_type"] == "file.uploaded"


@pytest.mark.asyncio
async def test_download_file(file_service, test_user, test_tenant, mock_storage_backend):
    """Test downloading a file."""
    # First upload a file
    file_content = b"test file content"
    filename = "test.pdf"

    file = await file_service.upload_file(
        file_content=file_content,
        filename=filename,
        entity_type=None,
        entity_id=None,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Now download it
    content, downloaded_file = await file_service.download_file(file.id, test_tenant.id)

    assert content == file_content
    assert downloaded_file.id == file.id
    mock_storage_backend.download.assert_called_once()


@pytest.mark.asyncio
async def test_delete_file(
    file_service, test_user, test_tenant, mock_storage_backend, mock_event_publisher
):
    """Test deleting a file."""
    # First upload a file
    file_content = b"test file content"
    filename = "test.pdf"

    file = await file_service.upload_file(
        file_content=file_content,
        filename=filename,
        entity_type=None,
        entity_id=None,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Delete it
    deleted = await file_service.delete_file(file.id, test_tenant.id, test_user.id)

    assert deleted is True

    # Verify file is soft deleted
    deleted_file = file_service.repository.get_by_id(file.id, test_tenant.id)
    assert deleted_file.is_current is False

    # Verify event was published
    publish_calls = [call for call in mock_event_publisher.publish.call_args_list]
    delete_calls = [
        call for call in publish_calls if call[1].get("event_type") == "file.deleted"
    ]
    assert len(delete_calls) > 0


@pytest.mark.asyncio
async def test_create_file_version(
    file_service, test_user, test_tenant, mock_storage_backend
):
    """Test creating a file version."""
    # First upload a file
    file_content = b"test file content"
    filename = "test.pdf"

    file = await file_service.upload_file(
        file_content=file_content,
        filename=filename,
        entity_type=None,
        entity_id=None,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Create a new version
    new_content = b"updated file content"
    version = await file_service.create_file_version(
        file_id=file.id,
        file_content=new_content,
        filename="test_v2.pdf",
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        change_description="Updated content",
    )

    assert version.file_id == file.id
    assert version.version_number == 2
    assert version.size == len(new_content)

    # Verify file version number was updated
    updated_file = file_service.repository.get_by_id(file.id, test_tenant.id)
    assert updated_file.version_number == 2


def test_get_file_versions(file_service, test_user, test_tenant):
    """Test getting file versions."""
    # This test would require creating a file with versions first
    # For now, just test the method exists and returns a list
    file_id = uuid4()
    versions = file_service.get_file_versions(file_id, test_tenant.id)
    assert isinstance(versions, list)


@pytest.mark.asyncio
async def test_generate_thumbnail(
    file_service, test_user, test_tenant, mock_storage_backend
):
    """Test generating thumbnail for an image."""
    from PIL import Image
    import io

    # Create a test image
    img = Image.new("RGB", (200, 200), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    file_content = img_bytes.getvalue()

    # Upload image
    file = await file_service.upload_file(
        file_content=file_content,
        filename="test.png",
        entity_type=None,
        entity_id=None,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Mock storage backend to return the image
    mock_storage_backend.download.return_value = file_content

    # Generate thumbnail
    thumbnail_bytes = await file_service.generate_thumbnail(
        file_id=file.id,
        tenant_id=test_tenant.id,
        width=50,
        height=50,
        quality=80,
    )

    # Verify thumbnail is valid JPEG
    thumbnail_img = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumbnail_img.format == "JPEG"
    assert thumbnail_img.width <= 50
    assert thumbnail_img.height <= 50


@pytest.mark.asyncio
async def test_generate_thumbnail_non_image(file_service, test_user, test_tenant):
    """Test that generate_thumbnail raises ValueError for non-image files."""
    # Upload a PDF file
    file_content = b"%PDF-1.4 test pdf content"
    file = await file_service.upload_file(
        file_content=file_content,
        filename="test.pdf",
        entity_type=None,
        entity_id=None,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    # Try to generate thumbnail
    with pytest.raises(ValueError, match="is not an image"):
        await file_service.generate_thumbnail(
            file_id=file.id,
            tenant_id=test_tenant.id,
            width=50,
            height=50,
        )

