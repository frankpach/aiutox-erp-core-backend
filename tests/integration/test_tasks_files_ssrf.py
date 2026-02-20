"""SSRF protection tests for Files API."""

import pytest
from fastapi import status


@pytest.mark.security
def test_file_url_blocks_localhost(client_with_db, tasks_manager_headers, task_factory):
    """Ensure localhost URLs are blocked."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "test.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "file_url": "http://localhost:8080/internal",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "not allowed" in data["error"]["message"].lower()


@pytest.mark.security
def test_file_url_blocks_127_0_0_1(client_with_db, tasks_manager_headers, task_factory):
    """Ensure 127.0.0.1 URLs are blocked."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "test.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "file_url": "http://127.0.0.1/file.pdf",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "not allowed" in data["error"]["message"].lower()


@pytest.mark.security
def test_file_url_blocks_private_ip_192_168(
    client_with_db, tasks_manager_headers, task_factory
):
    """Ensure private IP 192.168.x.x are blocked."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "test.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "file_url": "http://192.168.1.1/file.pdf",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.security
def test_file_url_blocks_private_ip_10(
    client_with_db, tasks_manager_headers, task_factory
):
    """Ensure private IP 10.x.x.x are blocked."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "test.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "file_url": "http://10.0.0.1/file.pdf",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.security
def test_file_url_blocks_private_ip_172(
    client_with_db, tasks_manager_headers, task_factory
):
    """Ensure private IP 172.16.x.x are blocked."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "test.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "file_url": "http://172.16.0.1/file.pdf",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.security
def test_file_size_too_large(client_with_db, tasks_manager_headers, task_factory):
    """Ensure file size limits are enforced (> 50MB)."""
    task = task_factory()

    # File too large (> 50MB)
    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "huge.pdf",
            "file_size": 60 * 1024 * 1024,  # 60MB
            "file_type": "application/pdf",
            "file_url": "https://example.com/file.pdf",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "exceeds maximum" in data["error"]["message"].lower()


@pytest.mark.security
def test_file_size_zero(client_with_db, tasks_manager_headers, task_factory):
    """Ensure file size must be greater than 0."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "empty.pdf",
            "file_size": 0,
            "file_type": "application/pdf",
            "file_url": "https://example.com/file.pdf",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    # La validación puede fallar por parámetros faltantes o por tamaño inválido
    assert (
        "required" in data["error"]["message"].lower()
        or "must be greater than 0" in data["error"]["message"].lower()
    )


@pytest.mark.security
def test_file_type_executable_blocked(
    client_with_db, tasks_manager_headers, task_factory
):
    """Ensure executable file types are blocked."""
    task = task_factory()

    # Executable file
    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "malware.exe",
            "file_size": 1024,
            "file_type": "application/x-msdownload",
            "file_url": "https://example.com/file.exe",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "not allowed" in data["error"]["message"].lower()


@pytest.mark.security
def test_file_type_script_blocked(client_with_db, tasks_manager_headers, task_factory):
    """Ensure script file types are blocked."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "script.sh",
            "file_size": 1024,
            "file_type": "application/x-sh",
            "file_url": "https://example.com/script.sh",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.security
def test_file_url_requires_http_or_https(
    client_with_db, tasks_manager_headers, task_factory
):
    """Ensure only HTTP/HTTPS URLs are allowed."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "file.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "file_url": "ftp://example.com/file.pdf",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "http" in data["error"]["message"].lower()


@pytest.mark.security
def test_valid_file_url_allowed(client_with_db, tasks_manager_headers, task_factory):
    """Ensure valid public URLs are allowed."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
        params={
            "file_id": "123e4567-e89b-12d3-a456-426614174000",
            "file_name": "document.pdf",
            "file_size": 1024,
            "file_type": "application/pdf",
            "file_url": "https://www.example.com/files/document.pdf",
        },
    )

    # Should succeed (201) or fail for other reasons (404 task not found, etc.)
    # but NOT fail with 400 for URL validation
    assert (
        response.status_code != status.HTTP_400_BAD_REQUEST
        or "url" not in response.json()["error"]["message"].lower()
    )
