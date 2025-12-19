"""Workflow service for workflow management."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task import Workflow, WorkflowExecution, WorkflowStep
from app.repositories.task_repository import WorkflowRepository

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for workflow management."""

    def __init__(self, db: Session):
        """Initialize workflow service.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = WorkflowRepository(db)

    def create_workflow(
        self,
        name: str,
        tenant_id: UUID,
        description: str | None = None,
        definition: dict[str, Any] | None = None,
        enabled: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> Workflow:
        """Create a new workflow.

        Args:
            name: Workflow name
            tenant_id: Tenant ID
            description: Workflow description (optional)
            definition: Workflow definition as JSON (optional)
            enabled: Whether workflow is enabled (default: True)
            metadata: Additional metadata (optional)

        Returns:
            Created Workflow object
        """
        workflow = self.repository.create_workflow(
            {
                "tenant_id": tenant_id,
                "name": name,
                "description": description,
                "definition": definition or {},
                "enabled": enabled,
                "metadata": metadata,
            }
        )

        logger.info(f"Workflow created: {workflow.id} ({name})")
        return workflow

    def get_workflow(self, workflow_id: UUID, tenant_id: UUID) -> Workflow | None:
        """Get a workflow by ID.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID

        Returns:
            Workflow object or None if not found
        """
        return self.repository.get_workflow_by_id(workflow_id, tenant_id)

    def get_workflows(
        self, tenant_id: UUID, enabled_only: bool = False, skip: int = 0, limit: int = 100
    ) -> list[Workflow]:
        """Get workflows for a tenant.

        Args:
            tenant_id: Tenant ID
            enabled_only: Only return enabled workflows (default: False)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Workflow objects
        """
        return self.repository.get_all_workflows(tenant_id, enabled_only, skip, limit)

    def update_workflow(
        self, workflow_id: UUID, tenant_id: UUID, workflow_data: dict
    ) -> Workflow | None:
        """Update a workflow.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID
            workflow_data: Workflow data to update

        Returns:
            Updated Workflow object or None if not found
        """
        return self.repository.update_workflow(workflow_id, tenant_id, workflow_data)

    def delete_workflow(self, workflow_id: UUID, tenant_id: UUID) -> bool:
        """Delete a workflow.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID

        Returns:
            True if deleted successfully, False otherwise
        """
        return self.repository.delete_workflow(workflow_id, tenant_id)

    def create_workflow_step(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        name: str,
        step_type: str,
        order: int,
        config: dict[str, Any] | None = None,
        transitions: list[dict] | None = None,
    ) -> WorkflowStep:
        """Create a workflow step.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID
            name: Step name
            step_type: Step type (e.g., 'task', 'approval', 'condition')
            order: Step order
            config: Step configuration (optional)
            transitions: Step transitions (optional)

        Returns:
            Created WorkflowStep object
        """
        return self.repository.create_workflow_step(
            {
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "name": name,
                "step_type": step_type,
                "order": order,
                "config": config,
                "transitions": transitions,
            }
        )

    def get_workflow_steps(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowStep]:
        """Get all steps for a workflow.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID

        Returns:
            List of WorkflowStep objects
        """
        return self.repository.get_workflow_steps(workflow_id, tenant_id)

    def start_workflow_execution(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        execution_data: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Start a workflow execution.

        Args:
            workflow_id: Workflow ID
            tenant_id: Tenant ID
            entity_type: Related entity type (optional)
            entity_id: Related entity ID (optional)
            execution_data: Initial execution data (optional)

        Returns:
            Created WorkflowExecution object
        """
        workflow = self.get_workflow(workflow_id, tenant_id)
        if not workflow or not workflow.enabled:
            raise ValueError(f"Workflow {workflow_id} not found or not enabled")

        # Get first step
        steps = self.get_workflow_steps(workflow_id, tenant_id)
        first_step = next((s for s in steps if s.order == 0), None)

        execution = self.repository.create_execution(
            {
                "workflow_id": workflow_id,
                "tenant_id": tenant_id,
                "status": "running",
                "current_step_id": first_step.id if first_step else None,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "execution_data": execution_data or {},
            }
        )

        logger.info(f"Workflow execution started: {execution.id} for workflow {workflow_id}")
        return execution

    def update_execution(
        self, execution_id: UUID, tenant_id: UUID, execution_data: dict
    ) -> WorkflowExecution | None:
        """Update a workflow execution.

        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID
            execution_data: Execution data to update

        Returns:
            Updated WorkflowExecution object or None if not found
        """
        execution = self.repository.update_execution(execution_id, tenant_id, execution_data)

        # If status changed to completed or failed, set completed_at
        if execution and execution_data.get("status") in ["completed", "failed", "cancelled"]:
            execution.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(execution)

        return execution








