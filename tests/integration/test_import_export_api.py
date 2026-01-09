"""Integration tests for Import/Export API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_import_job(client_with_db, test_user, auth_headers, db_session):
    """Test creating an import job."""
    # Assign import_export.import permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="import_export",
        role_name="importer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    job_data = {
        "module": "products",
        "file_name": "products.csv",
    }

    response = client_with_db.post(
        "/api/v1/import-export/import/jobs",
        json=job_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["module"] == "products"
    assert data["file_name"] == "products.csv"
    assert "id" in data


def test_list_import_jobs(client_with_db, test_user, auth_headers, db_session):
    """Test listing import jobs."""
    # Assign import_export.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="import_export",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client_with_db.get(
        "/api/v1/import-export/import/jobs",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_create_export_job(client_with_db, test_user, auth_headers, db_session):
    """Test creating an export job."""
    # Assign import_export.export permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="import_export",
        role_name="exporter",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    job_data = {
        "module": "products",
        "export_format": "csv",
    }

    response = client_with_db.post(
        "/api/v1/import-export/export/jobs",
        json=job_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["module"] == "products"
    assert data["export_format"] == "csv"
    assert "id" in data








