"""Integration tests for Files configuration API endpoints."""

import pytest
from uuid import uuid4

from tests.helpers import create_user_with_system_permission


def test_get_storage_config(client_with_db, test_user, db_session):
    """Test getting storage configuration."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    response = client_with_db.get("/api/v1/config/files/storage", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "backend" in data
    assert data["backend"] in ("local", "s3", "hybrid")


def test_update_storage_config_local(client_with_db, test_user, db_session):
    """Test updating storage configuration to local."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    config = {
        "backend": "local",
        "local": {
            "base_path": "/custom/storage",
        },
    }

    response = client_with_db.put(
        "/api/v1/config/files/storage",
        json=config,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["backend"] == "local"
    assert data["local"]["base_path"] == "/custom/storage"


def test_update_storage_config_invalid_backend(client_with_db, test_user, db_session):
    """Test updating storage configuration with invalid backend."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    config = {"backend": "invalid"}

    response = client_with_db.put(
        "/api/v1/config/files/storage",
        json=config,
        headers=headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_BACKEND"


def test_update_storage_config_s3_missing_bucket(client_with_db, test_user, db_session):
    """Test updating storage configuration to S3 without bucket name."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    config = {
        "backend": "s3",
        "s3": {
            "access_key_id": "test-key",
            "secret_access_key": "test-secret",
            "region": "us-east-1",
        },
    }

    response = client_with_db.put(
        "/api/v1/config/files/storage",
        json=config,
        headers=headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "MISSING_BUCKET_NAME"


def test_get_storage_stats(client_with_db, test_user, db_session):
    """Test getting storage statistics."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    response = client_with_db.get("/api/v1/config/files/stats", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_space_used" in data
    assert "total_files" in data
    assert "total_folders" in data
    assert "mime_distribution" in data
    assert isinstance(data["total_space_used"], int)
    assert isinstance(data["total_files"], int)
    assert isinstance(data["total_folders"], int)


def test_get_file_limits(client_with_db, test_user, db_session):
    """Test getting file limits configuration."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    response = client_with_db.get("/api/v1/config/files/limits", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "max_file_size" in data
    assert "allowed_mime_types" in data
    assert "blocked_mime_types" in data
    assert "max_versions_per_file" in data


def test_update_file_limits(client_with_db, test_user, db_session):
    """Test updating file limits configuration."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    limits = {
        "max_file_size": 50 * 1024 * 1024,  # 50MB
        "allowed_mime_types": ["image/*", "application/pdf"],
        "max_versions_per_file": 5,
    }

    response = client_with_db.put(
        "/api/v1/config/files/limits",
        json=limits,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["max_file_size"] == 50 * 1024 * 1024
    assert "image/*" in data["allowed_mime_types"]
    assert data["max_versions_per_file"] == 5


def test_update_file_limits_invalid_max_size(client_with_db, test_user, db_session):
    """Test updating file limits with invalid max file size."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    limits = {"max_file_size": -1}

    response = client_with_db.put(
        "/api/v1/config/files/limits",
        json=limits,
        headers=headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_MAX_FILE_SIZE"


def test_update_file_limits_invalid_mime_type(client_with_db, test_user, db_session):
    """Test updating file limits with invalid MIME type format."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    limits = {"allowed_mime_types": ["invalid-mime-type"]}

    response = client_with_db.put(
        "/api/v1/config/files/limits",
        json=limits,
        headers=headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_MIME_TYPE_FORMAT"


def test_get_thumbnail_config(client_with_db, test_user, db_session):
    """Test getting thumbnail configuration."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    response = client_with_db.get("/api/v1/config/files/thumbnails", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert "default_width" in data
    assert "default_height" in data
    assert "quality" in data
    assert "cache_enabled" in data


def test_update_thumbnail_config(client_with_db, test_user, db_session):
    """Test updating thumbnail configuration."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    config = {
        "default_width": 400,
        "default_height": 400,
        "quality": 90,
        "cache_enabled": True,
    }

    response = client_with_db.put(
        "/api/v1/config/files/thumbnails",
        json=config,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["default_width"] == 400
    assert data["default_height"] == 400
    assert data["quality"] == 90


def test_update_thumbnail_config_invalid_quality(client_with_db, test_user, db_session):
    """Test updating thumbnail configuration with invalid quality."""
    # Assign system.configure permission (admin role has system.configure)
    headers = create_user_with_system_permission(db_session, test_user, "admin")

    config = {"quality": 101}

    response = client_with_db.put(
        "/api/v1/config/files/thumbnails",
        json=config,
        headers=headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_QUALITY"


def test_config_endpoints_require_permission(client_with_db, test_user, db_session):
    """Test that configuration endpoints require system.configure permission."""
    # Create user without system.configure permission
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {token}"}

    # Try to access configuration endpoint
    response = client_with_db.get("/api/v1/config/files/storage", headers=headers)

    assert response.status_code == 403



