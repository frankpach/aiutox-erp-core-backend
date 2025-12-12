"""Integration tests for Reporting API endpoints."""

import pytest
from app.models.module_role import ModuleRole


def test_create_report(client, test_user, auth_headers, db_session):
    """Test creating a report definition."""
    # Assign reporting.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="reporting",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    report_data = {
        "name": "Products Report",
        "description": "Report of all products",
        "data_source_type": "products",
        "visualization_type": "table",
        "filters": {},
        "config": {},
    }

    response = client.post(
        "/api/v1/reporting/reports",
        json=report_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Products Report"
    assert data["data_source_type"] == "products"
    assert "id" in data


def test_list_reports(client, test_user, auth_headers, db_session):
    """Test listing reports."""
    # Assign reporting.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="reporting",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    from app.repositories.reporting_repository import ReportingRepository

    repo = ReportingRepository(db_session)
    repo.create_report(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Report",
            "data_source_type": "products",
            "visualization_type": "table",
            "created_by": test_user.id,
        }
    )

    response = client.get("/api/v1/reporting/reports", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0


def test_get_report(client, test_user, auth_headers, db_session):
    """Test getting a specific report."""
    # Assign reporting.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="reporting",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    from app.repositories.reporting_repository import ReportingRepository

    repo = ReportingRepository(db_session)
    report = repo.create_report(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Report",
            "data_source_type": "products",
            "visualization_type": "table",
            "created_by": test_user.id,
        }
    )

    response = client.get(
        f"/api/v1/reporting/reports/{report.id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(report.id)
    assert data["name"] == "Test Report"


def test_list_data_sources(client, test_user, auth_headers, db_session):
    """Test listing available data sources."""
    # Assign reporting.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="reporting",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/reporting/data-sources", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert any(ds["type"] == "products" for ds in data)


def test_get_data_source_columns(client, test_user, auth_headers, db_session):
    """Test getting columns for a data source."""
    # Assign reporting.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="reporting",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get(
        "/api/v1/reporting/data-sources/products/columns", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("name" in col and "type" in col for col in data)


def test_get_data_source_filters(client, test_user, auth_headers, db_session):
    """Test getting filters for a data source."""
    # Assign reporting.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="reporting",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get(
        "/api/v1/reporting/data-sources/products/filters", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0

