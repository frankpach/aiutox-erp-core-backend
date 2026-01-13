"""Integration tests for Flow Runs module interactions with Approvals module."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_flow_run_created_with_approval_request(client_with_db, test_user, auth_headers, db_session):
    """Test that a flow run is automatically created when an approval request is created."""
    # Assign permissions
    approval_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(approval_role)
    db_session.commit()

    # Create flow
    flow_data = {
        "name": "Test Flow",
        "flow_type": "sequential",
        "module": "orders",
    }
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Add step
    step_data = {
        "flow_id": flow_id,
        "step_order": 1,
        "name": "Step 1",
        "approver_type": "user",
        "approver_id": str(test_user.id),
    }
    step_response = client_with_db.post(
        f"/api/v1/approvals/flows/{flow_id}/steps",
        json=step_data,
        headers=auth_headers,
    )
    assert step_response.status_code == 201

    # Create request
    entity_id = uuid4()
    request_data = {
        "flow_id": flow_id,
        "title": "Test Request",
        "entity_type": "order",
        "entity_id": str(entity_id),
    }
    request_response = client_with_db.post(
        "/api/v1/approvals/requests",
        json=request_data,
        headers=auth_headers,
    )
    assert request_response.status_code == 201
    request_id = request_response.json()["data"]["id"]

    # Verify flow run was created
    flow_run_response = client_with_db.get(
        f"/api/v1/flow-runs/by-entity?entity_type=order&entity_id={entity_id}",
        headers=auth_headers,
    )
    assert flow_run_response.status_code == 200
    flow_run = flow_run_response.json()["data"]
    assert flow_run["status"] == "pending"
    assert flow_run["entity_type"] == "order"
    assert flow_run["entity_id"] == str(entity_id)
    assert flow_run["metadata"]["approval_request_id"] == str(request_id)


def test_flow_run_completed_on_approval(client_with_db, test_user, auth_headers, db_session):
    """Test that a flow run is completed when an approval request is approved."""
    # Assign permissions
    approval_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="manager",
        granted_by=test_user.id,
    )
    approver_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="approver",
        granted_by=test_user.id,
    )
    db_session.add(approval_role)
    db_session.add(approver_role)
    db_session.commit()

    # Create flow
    flow_data = {
        "name": "Test Flow",
        "flow_type": "sequential",
        "module": "orders",
    }
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Add step
    step_data = {
        "flow_id": flow_id,
        "step_order": 1,
        "name": "Step 1",
        "approver_type": "user",
        "approver_id": str(test_user.id),
    }
    step_response = client_with_db.post(
        f"/api/v1/approvals/flows/{flow_id}/steps",
        json=step_data,
        headers=auth_headers,
    )
    assert step_response.status_code == 201

    # Create request
    entity_id = uuid4()
    request_data = {
        "flow_id": flow_id,
        "title": "Test Request",
        "entity_type": "order",
        "entity_id": str(entity_id),
    }
    request_response = client_with_db.post(
        "/api/v1/approvals/requests",
        json=request_data,
        headers=auth_headers,
    )
    assert request_response.status_code == 201
    request_id = request_response.json()["data"]["id"]

    # Get flow run
    flow_run_response = client_with_db.get(
        f"/api/v1/flow-runs/by-entity?entity_type=order&entity_id={entity_id}",
        headers=auth_headers,
    )
    flow_run = flow_run_response.json()["data"]
    flow_run_id = flow_run["id"]
    assert flow_run["status"] == "pending"

    # Approve request
    approve_response = client_with_db.post(
        f"/api/v1/approvals/requests/{request_id}/approve?comment=Approved",
        headers=auth_headers,
    )
    assert approve_response.status_code == 200

    # Verify flow run was completed
    flow_run_response = client_with_db.get(
        f"/api/v1/flow-runs/{flow_run_id}",
        headers=auth_headers,
    )
    flow_run = flow_run_response.json()["data"]
    assert flow_run["status"] == "completed"
    assert flow_run["completed_at"] is not None
    assert flow_run["metadata"]["approved_by"] == str(test_user.id)


def test_flow_run_failed_on_rejection(client_with_db, test_user, auth_headers, db_session):
    """Test that a flow run is failed when an approval request is rejected."""
    # Assign permissions
    approval_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="manager",
        granted_by=test_user.id,
    )
    approver_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="approver",
        granted_by=test_user.id,
    )
    db_session.add(approval_role)
    db_session.add(approver_role)
    db_session.commit()

    # Create flow
    flow_data = {
        "name": "Test Flow",
        "flow_type": "sequential",
        "module": "orders",
    }
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Add step
    step_data = {
        "flow_id": flow_id,
        "step_order": 1,
        "name": "Step 1",
        "approver_type": "user",
        "approver_id": str(test_user.id),
    }
    step_response = client_with_db.post(
        f"/api/v1/approvals/flows/{flow_id}/steps",
        json=step_data,
        headers=auth_headers,
    )
    assert step_response.status_code == 201

    # Create request
    entity_id = uuid4()
    request_data = {
        "flow_id": flow_id,
        "title": "Test Request",
        "entity_type": "order",
        "entity_id": str(entity_id),
    }
    request_response = client_with_db.post(
        "/api/v1/approvals/requests",
        json=request_data,
        headers=auth_headers,
    )
    assert request_response.status_code == 201
    request_id = request_response.json()["data"]["id"]

    # Get flow run
    flow_run_response = client_with_db.get(
        f"/api/v1/flow-runs/by-entity?entity_type=order&entity_id={entity_id}",
        headers=auth_headers,
    )
    flow_run = flow_run_response.json()["data"]
    flow_run_id = flow_run["id"]
    assert flow_run["status"] == "pending"

    # Reject request
    reject_response = client_with_db.post(
        f"/api/v1/approvals/requests/{request_id}/reject?comment=Rejected",
        headers=auth_headers,
    )
    assert reject_response.status_code == 200

    # Verify flow run was failed
    flow_run_response = client_with_db.get(
        f"/api/v1/flow-runs/{flow_run_id}",
        headers=auth_headers,
    )
    flow_run = flow_run_response.json()["data"]
    assert flow_run["status"] == "failed"
    assert flow_run["completed_at"] is not None
    assert flow_run["error_message"] == "Approval request rejected"
    assert flow_run["metadata"]["rejected_by"] == str(test_user.id)


def test_flow_runs_stats(client_with_db, test_user, auth_headers, db_session):
    """Test flow runs statistics endpoint."""
    # Assign permissions
    stats_role = ModuleRole(
        user_id=test_user.id,
        module="flow_runs",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(stats_role)
    db_session.commit()

    # Get stats
    stats_response = client_with_db.get(
        "/api/v1/flow-runs/stats",
        headers=auth_headers,
    )
    assert stats_response.status_code == 200
    stats = stats_response.json()["data"]
    assert "total" in stats
    assert "pending" in stats
    assert "running" in stats
    assert "completed" in stats
    assert "failed" in stats
    assert stats["total"] >= 0
