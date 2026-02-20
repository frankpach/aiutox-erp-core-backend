"""Unit tests for WorkflowService."""

from uuid import uuid4

import pytest

from app.core.tasks.workflow_service import WorkflowService


@pytest.fixture
def workflow_service(db_session):
    """Create WorkflowService instance."""
    return WorkflowService(db=db_session)


def test_create_workflow(workflow_service, test_tenant):
    """Test creating a workflow."""
    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        tenant_id=test_tenant.id,
        description="Test description",
        definition={"steps": []},
        enabled=True,
    )

    assert workflow.name == "Test Workflow"
    assert workflow.description == "Test description"
    assert workflow.enabled is True
    assert workflow.tenant_id == test_tenant.id
    assert workflow.definition == {"steps": []}


def test_get_workflow(workflow_service, test_tenant):
    """Test getting a workflow."""
    # Create a workflow first
    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        tenant_id=test_tenant.id,
        definition={"steps": []},
    )

    # Get it
    retrieved_workflow = workflow_service.get_workflow(workflow.id, test_tenant.id)

    assert retrieved_workflow is not None
    assert retrieved_workflow.id == workflow.id
    assert retrieved_workflow.name == "Test Workflow"


def test_get_workflows(workflow_service, test_tenant):
    """Test getting workflows."""
    # Create multiple workflows
    workflow1 = workflow_service.create_workflow(
        name="Workflow 1",
        tenant_id=test_tenant.id,
        definition={"steps": []},
        enabled=True,
    )
    workflow2 = workflow_service.create_workflow(
        name="Workflow 2",
        tenant_id=test_tenant.id,
        definition={"steps": []},
        enabled=False,
    )

    # Get all workflows
    workflows = workflow_service.get_workflows(test_tenant.id)
    assert len(workflows) >= 2

    # Get only enabled workflows
    enabled_workflows = workflow_service.get_workflows(
        test_tenant.id, enabled_only=True
    )
    assert any(w.id == workflow1.id for w in enabled_workflows)
    assert not any(w.id == workflow2.id for w in enabled_workflows)


def test_update_workflow(workflow_service, test_tenant):
    """Test updating a workflow."""
    # Create a workflow
    workflow = workflow_service.create_workflow(
        name="Original Name",
        tenant_id=test_tenant.id,
        definition={"steps": []},
        enabled=True,
    )

    # Update it
    updated_workflow = workflow_service.update_workflow(
        workflow.id,
        test_tenant.id,
        {"name": "Updated Name", "enabled": False},
    )

    assert updated_workflow is not None
    assert updated_workflow.name == "Updated Name"
    assert updated_workflow.enabled is False


def test_delete_workflow(workflow_service, test_tenant):
    """Test deleting a workflow."""
    # Create a workflow
    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        tenant_id=test_tenant.id,
        definition={"steps": []},
    )

    # Delete it
    deleted = workflow_service.delete_workflow(workflow.id, test_tenant.id)

    assert deleted is True

    # Verify it's deleted
    retrieved_workflow = workflow_service.get_workflow(workflow.id, test_tenant.id)
    assert retrieved_workflow is None


def test_create_workflow_step(workflow_service, test_tenant):
    """Test creating a workflow step."""
    # Create a workflow first
    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        tenant_id=test_tenant.id,
        definition={"steps": []},
    )

    # Create a step
    step = workflow_service.create_workflow_step(
        workflow_id=workflow.id,
        tenant_id=test_tenant.id,
        name="Step 1",
        step_type="task",
        order=0,
        config={"action": "create_task"},
    )

    assert step.name == "Step 1"
    assert step.step_type == "task"
    assert step.order == 0
    assert step.workflow_id == workflow.id


def test_get_workflow_steps(workflow_service, test_tenant):
    """Test getting workflow steps."""
    # Create a workflow
    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        tenant_id=test_tenant.id,
        definition={"steps": []},
    )

    # Create multiple steps
    step1 = workflow_service.create_workflow_step(
        workflow_id=workflow.id,
        tenant_id=test_tenant.id,
        name="Step 1",
        step_type="task",
        order=0,
    )
    step2 = workflow_service.create_workflow_step(
        workflow_id=workflow.id,
        tenant_id=test_tenant.id,
        name="Step 2",
        step_type="approval",
        order=1,
    )

    # Get all steps
    steps = workflow_service.get_workflow_steps(workflow.id, test_tenant.id)

    assert len(steps) >= 2
    assert any(s.id == step1.id for s in steps)
    assert any(s.id == step2.id for s in steps)
    # Steps should be ordered
    step_orders = [s.order for s in steps]
    assert step_orders == sorted(step_orders)


def test_start_workflow_execution(workflow_service, test_tenant):
    """Test starting a workflow execution."""
    # Create a workflow with a step
    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        tenant_id=test_tenant.id,
        definition={"steps": []},
        enabled=True,
    )

    step = workflow_service.create_workflow_step(
        workflow_id=workflow.id,
        tenant_id=test_tenant.id,
        name="Step 1",
        step_type="task",
        order=0,
    )

    # Start execution
    execution = workflow_service.start_workflow_execution(
        workflow_id=workflow.id,
        tenant_id=test_tenant.id,
        entity_type="product",
        entity_id=uuid4(),
        execution_data={"test": "data"},
    )

    assert execution.workflow_id == workflow.id
    assert execution.status == "running"
    assert execution.entity_type == "product"
    assert execution.current_step_id == step.id


def test_start_workflow_execution_disabled_workflow(workflow_service, test_tenant):
    """Test starting execution on disabled workflow raises error."""
    # Create a disabled workflow
    workflow = workflow_service.create_workflow(
        name="Disabled Workflow",
        tenant_id=test_tenant.id,
        definition={"steps": []},
        enabled=False,
    )

    # Try to start execution
    with pytest.raises(ValueError, match="not found or not enabled"):
        workflow_service.start_workflow_execution(
            workflow_id=workflow.id,
            tenant_id=test_tenant.id,
        )


def test_update_execution(workflow_service, test_tenant):
    """Test updating a workflow execution."""
    # Create workflow and start execution
    workflow = workflow_service.create_workflow(
        name="Test Workflow",
        tenant_id=test_tenant.id,
        definition={"steps": []},
        enabled=True,
    )

    workflow_service.create_workflow_step(
        workflow_id=workflow.id,
        tenant_id=test_tenant.id,
        name="Step 1",
        step_type="task",
        order=0,
    )

    execution = workflow_service.start_workflow_execution(
        workflow_id=workflow.id,
        tenant_id=test_tenant.id,
    )

    # Update execution
    updated_execution = workflow_service.update_execution(
        execution.id,
        test_tenant.id,
        {"status": "completed", "execution_data": {"result": "success"}},
    )

    assert updated_execution is not None
    assert updated_execution.status == "completed"
    assert updated_execution.completed_at is not None
