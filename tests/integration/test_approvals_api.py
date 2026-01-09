"""Integration tests for Approvals API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_approval_flow(client_with_db, test_user, auth_headers, db_session):
    """Test creating an approval flow."""
    # Assign approvals.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    flow_data = {
        "name": "Test Flow",
        "flow_type": "sequential",
        "module": "orders",
    }

    response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Flow"
    assert data["flow_type"] == "sequential"
    assert "id" in data


def test_create_approval_request(client_with_db, test_user, auth_headers, db_session):
    """Test creating an approval request."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Create request
    entity_id = uuid4()
    request_data = {
        "flow_id": flow_id,
        "title": "Test Request",
        "entity_type": "order",
        "entity_id": str(entity_id),
    }

    response = client_with_db.post(
        "/api/v1/approvals/requests",
        json=request_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Test Request"
    assert data["status"] == "pending"
    assert "id" in data








