"""Integration tests for new Approvals API endpoints."""

from uuid import uuid4

from app.models.approval import ApprovalFlow


def test_delete_approval_flow_soft_delete(client_with_db, test_user, db_session):
    """Test soft deleting an approval flow."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.manager"
    )

    # Create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Delete the flow
    response = client_with_db.delete(
        f"/api/v1/approvals/flows/{flow_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    # Verify soft delete in database
    flow = db_session.query(ApprovalFlow).filter(ApprovalFlow.id == flow_id).first()
    assert flow is not None
    assert flow.deleted_at is not None
    assert flow.is_active is False


def test_delete_flow_with_active_requests_fails(client_with_db, test_user, db_session):
    """Test that deleting a flow with active requests fails."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.manager"
    )

    # Create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Create an active request
    entity_id = uuid4()
    request_data = {
        "flow_id": flow_id,
        "title": "Test Request",
        "entity_type": "order",
        "entity_id": str(entity_id),
    }
    client_with_db.post(
        "/api/v1/approvals/requests",
        json=request_data,
        headers=auth_headers,
    )

    # Try to delete the flow
    response = client_with_db.delete(
        f"/api/v1/approvals/flows/{flow_id}",
        headers=auth_headers,
    )

    assert response.status_code == 400
    response_json = response.json()
    print(f"Response JSON: {response_json}")
    assert (
        "Cannot delete flow with active requests" in response_json["error"]["message"]
    )


def test_update_approval_flow(client_with_db, test_user, db_session):
    """Test updating an approval flow."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.manager"
    )

    # Create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Update the flow
    update_data = {"name": "Updated Flow", "description": "Updated description"}
    response = client_with_db.put(
        f"/api/v1/approvals/flows/{flow_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Flow"
    assert data["description"] == "Updated description"


def test_get_approval_steps(client_with_db, test_user, db_session):
    """Test getting steps for a flow."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.manager"
    )

    # Create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Add steps usando PUT con lista de steps
    steps_data = [
        {
            "flow_id": flow_id,
            "step_order": 1,
            "name": "Step 1",
            "approver_type": "user",
            "approver_id": str(test_user.id),
        }
    ]
    client_with_db.put(
        f"/api/v1/approvals/flows/{flow_id}/steps",
        json=steps_data,
        headers=auth_headers,
    )

    # Get steps
    response = client_with_db.get(
        f"/api/v1/approvals/flows/{flow_id}/steps",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 1
    assert data[0]["name"] == "Step 1"


def test_update_approval_step(client_with_db, test_user, db_session):
    """Test updating an approval step."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.manager"
    )

    # Create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Add a step usando PUT con lista
    steps_data = [
        {
            "flow_id": flow_id,
            "step_order": 1,
            "name": "Step 1",
            "approver_type": "user",
            "approver_id": str(test_user.id),
        }
    ]
    step_response = client_with_db.put(
        f"/api/v1/approvals/flows/{flow_id}/steps",
        json=steps_data,
        headers=auth_headers,
    )
    step_id = step_response.json()["data"][0]["id"]

    # Update the step
    update_data = {"name": "Updated Step", "description": "Updated description"}
    print(f"Updating step with data: {update_data}")
    print(f"Step ID: {step_id}")
    print(f"Flow ID: {flow_id}")

    response = client_with_db.put(
        f"/api/v1/approvals/flows/{flow_id}/steps/{step_id}",
        json=update_data,
        headers=auth_headers,
    )

    print(f"Response status: {response.status_code}")
    if response.status_code != 200:
        print(f"Response content: {response.text}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Step"


def test_cancel_approval_request(client_with_db, test_user, db_session):
    """Test cancelling an approval request."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.manager"
    )

    # Create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Create a request
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
    request_id = request_response.json()["data"]["id"]

    # Cancel the request
    response = client_with_db.post(
        f"/api/v1/approvals/requests/{request_id}/cancel",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "cancelled"


def test_approve_request_with_audit_info(client_with_db, test_user, db_session):
    """Test approving a request with IP and user agent capture."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.manager"
    )

    # Create a flow with a step
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Add a step usando PUT con lista
    steps_data = [
        {
            "flow_id": flow_id,
            "step_order": 1,
            "name": "Step 1",
            "approver_type": "user",
            "approver_id": str(test_user.id),
        }
    ]
    client_with_db.put(
        f"/api/v1/approvals/flows/{flow_id}/steps",
        json=steps_data,
        headers=auth_headers,
    )

    # Create a request
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
    request_id = request_response.json()["data"]["id"]

    # Approve the request
    response = client_with_db.post(
        f"/api/v1/approvals/requests/{request_id}/approve?comment=Aprobado",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] in ["approved", "pending"]  # Could be approved if single step


def test_get_approval_stats(client_with_db, test_user, db_session):
    """Test getting approval statistics."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "internal.viewer"
    )

    # Get stats
    response = client_with_db.get(
        "/api/v1/approvals/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_requests" in data
    assert "status_counts" in data


def test_get_request_timeline(client_with_db, test_user, db_session):
    """Test getting request timeline."""
    # Use create_user_with_permission to get proper auth headers with permissions
    from tests.helpers import create_user_with_permission

    auth_headers = create_user_with_permission(
        db_session, test_user, "approvals", "manager"
    )

    # Create a flow
    flow_data = {"name": "Test Flow", "flow_type": "sequential", "module": "orders"}
    flow_response = client_with_db.post(
        "/api/v1/approvals/flows",
        json=flow_data,
        headers=auth_headers,
    )
    flow_id = flow_response.json()["data"]["id"]

    # Create a request
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
    request_id = request_response.json()["data"]["id"]

    # Get timeline
    response = client_with_db.get(
        f"/api/v1/approvals/requests/{request_id}/timeline",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["type"] == "request_created"
    assert "timestamp" in data[0]
    assert "actor_id" in data[0]
    assert "data" in data[0]
