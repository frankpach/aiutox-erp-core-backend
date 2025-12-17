"""Task repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.task import (
    Task,
    TaskChecklistItem,
    Workflow,
    WorkflowExecution,
    WorkflowStep,
)


class TaskRepository:
    """Repository for task data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Task operations
    def create_task(self, task_data: dict) -> Task:
        """Create a new task."""
        task = Task(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task_by_id(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Get task by ID and tenant."""
        return (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

    def get_all_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Get all tasks for a tenant with filters."""
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if assigned_to_id:
            query = query.filter(Task.assigned_to_id == assigned_to_id)
        return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_tasks_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> list[Task]:
        """Get tasks by related entity."""
        return (
            self.db.query(Task)
            .filter(
                Task.related_entity_type == entity_type,
                Task.related_entity_id == entity_id,
                Task.tenant_id == tenant_id,
            )
            .order_by(Task.created_at.desc())
            .all()
        )

    def update_task(self, task_id: UUID, tenant_id: UUID, task_data: dict) -> Task | None:
        """Update a task."""
        task = self.get_task_by_id(task_id, tenant_id)
        if not task:
            return None
        for key, value in task_data.items():
            setattr(task, key, value)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task_id: UUID, tenant_id: UUID) -> bool:
        """Delete a task."""
        task = self.get_task_by_id(task_id, tenant_id)
        if not task:
            return False
        self.db.delete(task)
        self.db.commit()
        return True

    # Checklist operations
    def create_checklist_item(self, item_data: dict) -> TaskChecklistItem:
        """Create a new checklist item."""
        item = TaskChecklistItem(**item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_checklist_items(self, task_id: UUID, tenant_id: UUID) -> list[TaskChecklistItem]:
        """Get all checklist items for a task."""
        return (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.task_id == task_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .order_by(TaskChecklistItem.order)
            .all()
        )

    def update_checklist_item(
        self, item_id: UUID, tenant_id: UUID, item_data: dict
    ) -> TaskChecklistItem | None:
        """Update a checklist item."""
        item = (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.id == item_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .first()
        )
        if not item:
            return None
        for key, value in item_data.items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_checklist_item(self, item_id: UUID, tenant_id: UUID) -> bool:
        """Delete a checklist item."""
        item = (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.id == item_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .first()
        )
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True


class WorkflowRepository:
    """Repository for workflow data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Workflow operations
    def create_workflow(self, workflow_data: dict) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(**workflow_data)
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_workflow_by_id(self, workflow_id: UUID, tenant_id: UUID) -> Workflow | None:
        """Get workflow by ID and tenant."""
        return (
            self.db.query(Workflow)
            .filter(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
            .first()
        )

    def get_all_workflows(
        self, tenant_id: UUID, enabled_only: bool = False, skip: int = 0, limit: int = 100
    ) -> list[Workflow]:
        """Get all workflows for a tenant."""
        query = self.db.query(Workflow).filter(Workflow.tenant_id == tenant_id)
        if enabled_only:
            query = query.filter(Workflow.enabled == True)
        return query.order_by(Workflow.created_at.desc()).offset(skip).limit(limit).all()

    def update_workflow(
        self, workflow_id: UUID, tenant_id: UUID, workflow_data: dict
    ) -> Workflow | None:
        """Update a workflow."""
        workflow = self.get_workflow_by_id(workflow_id, tenant_id)
        if not workflow:
            return None
        for key, value in workflow_data.items():
            setattr(workflow, key, value)
        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def delete_workflow(self, workflow_id: UUID, tenant_id: UUID) -> bool:
        """Delete a workflow."""
        workflow = self.get_workflow_by_id(workflow_id, tenant_id)
        if not workflow:
            return False
        self.db.delete(workflow)
        self.db.commit()
        return True

    # WorkflowStep operations
    def create_workflow_step(self, step_data: dict) -> WorkflowStep:
        """Create a new workflow step."""
        step = WorkflowStep(**step_data)
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_workflow_steps(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowStep]:
        """Get all steps for a workflow."""
        return (
            self.db.query(WorkflowStep)
            .filter(
                WorkflowStep.workflow_id == workflow_id,
                WorkflowStep.tenant_id == tenant_id,
            )
            .order_by(WorkflowStep.order)
            .all()
        )

    # WorkflowExecution operations
    def create_execution(self, execution_data: dict) -> WorkflowExecution:
        """Create a new workflow execution."""
        execution = WorkflowExecution(**execution_data)
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def get_execution_by_id(
        self, execution_id: UUID, tenant_id: UUID
    ) -> WorkflowExecution | None:
        """Get workflow execution by ID and tenant."""
        return (
            self.db.query(WorkflowExecution)
            .filter(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            )
            .first()
        )

    def update_execution(
        self, execution_id: UUID, tenant_id: UUID, execution_data: dict
    ) -> WorkflowExecution | None:
        """Update a workflow execution."""
        execution = self.get_execution_by_id(execution_id, tenant_id)
        if not execution:
            return None
        for key, value in execution_data.items():
            setattr(execution, key, value)
        self.db.commit()
        self.db.refresh(execution)
        return execution







