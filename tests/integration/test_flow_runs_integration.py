"""Integration tests for Flow Runs module interactions with Approvals module."""

from uuid import uuid4

from app.models.module_role import ModuleRole


def test_flow_run_created_with_approval_request(
    client_with_db, test_user, auth_headers, db_session
):
    """Test that a flow run is automatically created when an approval request is created."""
    # Assign permissions
    approval_role = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(approval_role)

    # Also assign flow_runs permissions
    flow_runs_role = ModuleRole(
        user_id=test_user.id,
        module="flow_runs",
        role_name="internal.manager",
        granted_by=test_user.id,
    )
    db_session.add(flow_runs_role)
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
    print(f"Creating approval request with data: {request_data}")
    request_response = client_with_db.post(
        "/api/v1/approvals/requests",
        json=request_data,
        headers=auth_headers,
    )
    assert request_response.status_code == 201
    request_id = request_response.json()["data"]["id"]
    print(f"Created approval request: {request_id}")

    # Verify flow run was created
    print(f"Checking if flow run was created for entity_id: {entity_id}")

    # Check directly in database
    from app.models.flow_run import FlowRun

    flow_run_db = (
        db_session.query(FlowRun)
        .filter(FlowRun.entity_type == "order", FlowRun.entity_id == entity_id)
        .first()
    )

    print(f"Flow run found in DB: {flow_run_db.id if flow_run_db else None}")

    flow_run_response = client_with_db.get(
        f"/api/v1/flow-runs/by-entity?entity_type=order&entity_id={entity_id}",
        headers=auth_headers,
    )
    print(f"Flow run response status: {flow_run_response.status_code}")
    print(f"Flow run response: {flow_run_response.json()}")
    assert flow_run_response.status_code == 200
    flow_run = flow_run_response.json()["data"]
    assert flow_run["status"] == "pending"
    assert flow_run["entity_type"] == "order"
    assert flow_run["entity_id"] == str(entity_id)
    assert flow_run["run_metadata"]["approval_request_id"] == str(request_id)


def test_flow_run_completed_on_approval(
    client_with_db, test_user, auth_headers, db_session
):
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
    flow_runs_role = ModuleRole(
        user_id=test_user.id,
        module="flow_runs",
        role_name="internal.manager",
        granted_by=test_user.id,
    )
    db_session.add(approval_role)
    db_session.add(approver_role)
    db_session.add(flow_runs_role)
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
    assert flow_run["run_metadata"]["approved_by"] == str(test_user.id)


def test_flow_run_failed_on_rejection(
    client_with_db, test_user, auth_headers, db_session
):
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
    flow_runs_role = ModuleRole(
        user_id=test_user.id,
        module="flow_runs",
        role_name="internal.manager",
        granted_by=test_user.id,
    )
    db_session.add(approval_role)
    db_session.add(approver_role)
    db_session.add(flow_runs_role)
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
    assert flow_run["run_metadata"]["rejected_by"] == str(test_user.id)


def test_flow_runs_stats(client_with_db, test_user, db_session):
    """Test flow runs statistics endpoint."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "flow_runs", "internal.viewer"
    )

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
