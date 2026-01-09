"""Integration tests for Reporting API endpoints."""

import pytest
from tests.helpers import create_user_with_permission


def test_create_report(client_with_db, test_user, db_session):
    """Test creating a report definition."""
    # Assign reporting.manage permission
    headers = create_user_with_permission(db_session, test_user, "reporting", "manager")

    report_data = {
        "name": "Products Report",
        "description": "Report of all products",
        "data_source_type": "products",
        "visualization_type": "table",
        "filters": {},
        "config": {},
    }

    response = client_with_db.post(
        "/api/v1/reporting/reports",
        json=report_data,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Products Report"
    assert data["data_source_type"] == "products"
    assert "id" in data


def test_list_reports(client_with_db, test_user, db_session):
    """Test listing reports."""
    # Assign reporting.view permission
    headers = create_user_with_permission(db_session, test_user, "reporting", "viewer")

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

    response = client_with_db.get("/api/v1/reporting/reports", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0


def test_get_report(client_with_db, test_user, db_session):
    """Test getting a specific report."""
    # Assign reporting.view permission
    headers = create_user_with_permission(db_session, test_user, "reporting", "viewer")

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

    response = client_with_db.get(
        f"/api/v1/reporting/reports/{report.id}", headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(report.id)
    assert data["name"] == "Test Report"


def test_list_data_sources(client_with_db, test_user, db_session):
    """Test listing available data sources."""
    # Assign reporting.view permission
    headers = create_user_with_permission(db_session, test_user, "reporting", "viewer")

    response = client_with_db.get("/api/v1/reporting/data-sources", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert any(ds["type"] == "products" for ds in data)


def test_get_data_source_columns(client_with_db, test_user, db_session):
    """Test getting columns for a data source."""
    # Assign reporting.view permission
    headers = create_user_with_permission(db_session, test_user, "reporting", "viewer")

    response = client_with_db.get(
        "/api/v1/reporting/data-sources/products/columns", headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("name" in col and "type" in col for col in data)


def test_get_data_source_filters(client_with_db, test_user, db_session):
    """Test getting filters for a data source."""
    # Assign reporting.view permission
    headers = create_user_with_permission(db_session, test_user, "reporting", "viewer")

    response = client_with_db.get(
        "/api/v1/reporting/data-sources/products/filters", headers=headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0

