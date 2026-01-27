"""Unit tests for ApprovalService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.core.approvals.service import ApprovalService, FlowEngine
from app.core.pubsub import EventPublisher


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def approval_service(db_session, mock_event_publisher):
    """Create ApprovalService instance."""
    return ApprovalService(db=db_session, event_publisher=mock_event_publisher)


def test_create_approval_flow(approval_service, test_user, test_tenant):
    """Test creating an approval flow."""
    flow = approval_service.create_approval_flow(
        flow_data={
            "name": "Test Flow",
            "flow_type": "sequential",
            "module": "orders",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert flow.name == "Test Flow"
    assert flow.flow_type == "sequential"
    assert flow.module == "orders"
    assert flow.tenant_id == test_tenant.id


def test_create_approval_request(approval_service, test_user, test_tenant, mock_event_publisher):
    """Test creating an approval request."""
    # First create a flow
    flow = approval_service.create_approval_flow(
        flow_data={
            "name": "Test Flow",
            "flow_type": "sequential",
            "module": "orders",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    entity_id = uuid4()
    request = approval_service.create_approval_request(
        request_data={
            "flow_id": flow.id,
            "title": "Test Request",
            "entity_type": "order",
            "entity_id": entity_id,
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert request.title == "Test Request"
    assert request.flow_id == flow.id
    assert request.entity_type == "order"
    assert request.entity_id == entity_id
    assert request.status == "pending"

    # Verify event was published
    assert mock_event_publisher.publish.called


def test_add_approval_step(approval_service, test_user, test_tenant):
    """Test adding an approval step to a flow."""
    flow = approval_service.create_approval_flow(
        flow_data={
            "name": "Test Flow",
            "flow_type": "sequential",
            "module": "orders",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    step = approval_service.add_approval_step(
        flow_id=flow.id,
        tenant_id=test_tenant.id,
        step_data={
            "step_order": 1,
            "name": "Step 1",
            "approver_type": "user",
            "approver_id": test_user.id,
        },
    )

    assert step.flow_id == flow.id
    assert step.step_order == 1
    assert step.approver_type == "user"
    assert step.approver_id == test_user.id
    assert step.name == "Step 1"


def test_bulk_approve_requests(approval_service, test_user, test_tenant, mock_event_publisher):
    """Test bulk approving multiple approval requests."""
    # Create a flow with steps
    flow = approval_service.create_approval_flow(
        flow_data={
            "name": "Test Flow",
            "flow_type": "sequential",
            "module": "orders",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    step = approval_service.add_approval_step(
        flow_id=flow.id,
        tenant_id=test_tenant.id,
        step_data={
            "step_order": 1,
            "name": "Step 1",
            "approver_type": "user",
            "approver_id": test_user.id,
        },
    )

    # Create multiple requests
    request_ids = []
    for i in range(3):
        entity_id = uuid4()
        request = approval_service.create_approval_request(
            request_data={
                "flow_id": flow.id,
                "title": f"Test Request {i}",
                "entity_type": "order",
                "entity_id": entity_id,
            },
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )
        request_ids.append(request.id)

    # Bulk approve
    print(f"Attempting to bulk approve {len(request_ids)} requests")
    print(f"Request IDs: {request_ids}")
    print(f"User ID: {test_user.id}")
    print(f"Tenant ID: {test_tenant.id}")

    approved_requests = approval_service.bulk_approve_requests(
        request_ids=request_ids,
        tenant_id=test_tenant.id,
        user_id=test_user.id,
        comment="Bulk approval test",
    )

    print(f"Approved requests count: {len(approved_requests)}")
    print(f"Approved requests: {approved_requests}")

    assert len(approved_requests) == 3
    for request in approved_requests:
        assert request.status == "approved"


