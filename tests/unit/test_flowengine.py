"""Unit tests for FlowEngine."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.approvals.service import FlowEngine
from app.models.approval import (
    ApprovalAction,
    ApprovalFlow,
    ApprovalRequest,
    ApprovalStep,
)


@pytest.fixture
def flow_engine(db_session):
    """Create FlowEngine instance."""
    return FlowEngine(db=db_session)


@pytest.fixture
def sequential_flow(test_tenant, test_user, db_session):
    """Create a sequential approval flow."""
    flow = ApprovalFlow(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Sequential Flow",
        description="Sequential approval flow",
        flow_type="sequential",
        module="orders",
        conditions=None,
        is_active=True,
        created_by=test_user.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(flow)
    db_session.commit()
    db_session.refresh(flow)
    return flow


@pytest.fixture
def parallel_flow(test_tenant, test_user, db_session):
    """Create a parallel approval flow."""
    flow = ApprovalFlow(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Parallel Flow",
        description="Parallel approval flow",
        flow_type="parallel",
        module="orders",
        conditions=None,
        is_active=True,
        created_by=test_user.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(flow)
    db_session.commit()
    db_session.refresh(flow)
    return flow


@pytest.fixture
def conditional_flow(test_tenant, test_user, db_session):
    """Create a conditional approval flow."""
    flow = ApprovalFlow(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Conditional Flow",
        description="Conditional approval flow",
        flow_type="sequential",
        module="orders",
        conditions={"step_2": {"amount": {"operator": "lt", "value": 1000}}},
        is_active=True,
        created_by=test_user.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(flow)
    db_session.commit()
    db_session.refresh(flow)
    return flow


@pytest.fixture
def approval_steps(db_session, sequential_flow, test_user):
    """Create approval steps for a flow."""
    steps = [
        ApprovalStep(
            id=uuid4(),
            tenant_id=sequential_flow.tenant_id,
            flow_id=sequential_flow.id,
            step_order=1,
            name="Step 1",
            description="First approval step",
            approver_type="user",
            approver_id=test_user.id,
            approver_role=None,
            approver_rule=None,
            require_all=False,
            min_approvals=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        ApprovalStep(
            id=uuid4(),
            tenant_id=sequential_flow.tenant_id,
            flow_id=sequential_flow.id,
            step_order=2,
            name="Step 2",
            description="Second approval step",
            approver_type="user",
            approver_id=test_user.id,
            approver_role=None,
            approver_rule=None,
            require_all=False,
            min_approvals=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
    ]
    for step in steps:
        db_session.add(step)
    db_session.commit()
    return steps


def test_get_next_step_sequential(
    flow_engine, sequential_flow, approval_steps, test_user
):
    """Test getting next step in sequential flow."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    next_step = flow_engine.get_next_step(request, sequential_flow)

    assert next_step is not None
    assert next_step.step_order == 2


def test_get_next_step_no_next(flow_engine, sequential_flow, approval_steps, test_user):
    """Test getting next step when at last step."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=2,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    next_step = flow_engine.get_next_step(request, sequential_flow)

    assert next_step is None


def test_get_current_step(flow_engine, sequential_flow, approval_steps, test_user):
    """Test getting current step."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    current_step = flow_engine.get_current_step(request, sequential_flow)

    assert current_step is not None
    assert current_step.step_order == 1


def test_can_approve_user_approver(
    flow_engine, sequential_flow, approval_steps, test_user
):
    """Test can_approve with user approver."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    can_approve = flow_engine.can_approve(request, test_user.id, sequential_flow)

    assert can_approve is True


def test_can_approve_wrong_user(
    flow_engine, sequential_flow, approval_steps, test_user
):
    """Test can_approve with wrong user."""
    wrong_user_id = uuid4()
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    can_approve = flow_engine.can_approve(request, wrong_user_id, sequential_flow)

    assert can_approve is False


def test_should_skip_step_no_conditions(
    flow_engine, sequential_flow, approval_steps, test_user
):
    """Test _should_skip_step when no conditions exist."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    should_skip = flow_engine._should_skip_step(
        approval_steps[0], request, sequential_flow
    )

    assert should_skip is False


def test_should_skip_step_condition_met(
    flow_engine, conditional_flow, test_user, db_session
):
    """Test _should_skip_step when condition is met."""
    # Create steps for conditional flow
    step1 = ApprovalStep(
        id=uuid4(),
        tenant_id=conditional_flow.tenant_id,
        flow_id=conditional_flow.id,
        step_order=1,
        name="Step 1",
        description="First step",
        approver_type="user",
        approver_id=test_user.id,
        approver_role=None,
        approver_rule=None,
        require_all=False,
        min_approvals=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    step2 = ApprovalStep(
        id=uuid4(),
        tenant_id=conditional_flow.tenant_id,
        flow_id=conditional_flow.id,
        step_order=2,
        name="Step 2",
        description="Second step (conditional)",
        approver_type="user",
        approver_id=test_user.id,
        approver_role=None,
        approver_rule=None,
        require_all=False,
        min_approvals=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(step1)
    db_session.add(step2)
    db_session.commit()

    # Create request with metadata that meets condition
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=conditional_flow.tenant_id,
        flow_id=conditional_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # Request without metadata won't skip
    should_skip = flow_engine._should_skip_step(step2, request, conditional_flow)
    assert should_skip is False


def test_process_approval_sequential(
    flow_engine, sequential_flow, approval_steps, test_user, db_session
):
    """Test processing approval in sequential flow."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(request)
    db_session.commit()

    updated_request = flow_engine.process_approval(
        request, test_user.id, "approve", "Aprobado", "192.168.1.1", "TestAgent/1.0"
    )

    assert updated_request.current_step == 2
    assert updated_request.status == "pending"

    # Verify action was created
    actions = (
        db_session.query(ApprovalAction)
        .filter(ApprovalAction.request_id == request.id)
        .all()
    )
    assert len(actions) == 1
    assert actions[0].action_type == "approve"
    assert actions[0].ip_address == "192.168.1.1"
    assert actions[0].user_agent == "TestAgent/1.0"


def test_process_approval_complete(
    flow_engine, sequential_flow, approval_steps, test_user, db_session
):
    """Test processing approval that completes the flow."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=2,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(request)
    db_session.commit()

    updated_request = flow_engine.process_approval(
        request, test_user.id, "approve", "Aprobado", "192.168.1.1", "TestAgent/1.0"
    )

    assert updated_request.status == "approved"
    assert updated_request.completed_at is not None


def test_process_approval_reject(
    flow_engine, sequential_flow, approval_steps, test_user, db_session
):
    """Test processing rejection."""
    request = ApprovalRequest(
        id=uuid4(),
        tenant_id=sequential_flow.tenant_id,
        flow_id=sequential_flow.id,
        title="Test Request",
        description="Test request",
        entity_type="order",
        entity_id=uuid4(),
        status="pending",
        current_step=1,
        requested_by=test_user.id,
        requested_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(request)
    db_session.commit()

    updated_request = flow_engine.process_approval(
        request, test_user.id, "reject", "Rechazado", "192.168.1.1", "TestAgent/1.0"
    )

    assert updated_request.status == "rejected"
    assert updated_request.completed_at is not None
