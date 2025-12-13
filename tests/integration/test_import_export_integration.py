"""Integration tests for Import/Export module interactions."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_import_job_lifecycle(client, test_user, auth_headers, db_session):
    """Test complete import job lifecycle."""
    # Assign permissions
    import_role = ModuleRole(
        user_id=test_user.id,
        module="import_export",
        role_name="importer",
        granted_by=test_user.id,
    )
    db_session.add(import_role)
    db_session.commit()

    # Create import job
    job_data = {
        "module": "products",
        "file_name": "products.csv",
    }
    job_response = client.post(
        "/api/v1/import-export/import/jobs",
        json=job_data,
        headers=auth_headers,
    )
    job_id = job_response.json()["data"]["id"]
    assert job_response.json()["data"]["status"] == "pending"

    # Get job status
    status_response = client.get(
        f"/api/v1/import-export/import/jobs/{job_id}",
        headers=auth_headers,
    )

    assert status_response.status_code == 200
    assert status_response.json()["data"]["status"] == "pending"


def test_import_template_reusability(client, test_user, auth_headers, db_session):
    """Test that import templates can be reused."""
    # Assign permissions
    import_role = ModuleRole(
        user_id=test_user.id,
        module="import_export",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(import_role)
    db_session.commit()

    # Create template
    template_data = {
        "name": "Products Import Template",
        "module": "products",
        "field_mapping": {
            "name": "product_name",
            "price": "product_price",
        },
        "skip_header": True,
        "delimiter": ",",
    }
    template_response = client.post(
        "/api/v1/import-export/import/templates",
        json=template_data,
        headers=auth_headers,
    )
    template_id = template_response.json()["data"]["id"]

    # Use template in import job
    job_data = {
        "module": "products",
        "file_name": "products.csv",
        "template_id": template_id,
    }
    job_response = client.post(
        "/api/v1/import-export/import/jobs",
        json=job_data,
        headers=auth_headers,
    )

    assert job_response.status_code == 201
    assert job_response.json()["data"]["template_id"] == template_id


def test_export_multiple_formats(client, test_user, auth_headers, db_session):
    """Test exporting to different formats."""
    # Assign permissions
    export_role = ModuleRole(
        user_id=test_user.id,
        module="import_export",
        role_name="exporter",
        granted_by=test_user.id,
    )
    db_session.add(export_role)
    db_session.commit()

    formats = ["csv", "excel", "pdf"]

    for export_format in formats:
        job_data = {
            "module": "products",
            "export_format": export_format,
        }
        job_response = client.post(
            "/api/v1/import-export/export/jobs",
            json=job_data,
            headers=auth_headers,
        )

        assert job_response.status_code == 201
        assert job_response.json()["data"]["export_format"] == export_format

