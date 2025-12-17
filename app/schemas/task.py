"""Task schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    """Base schema for task."""

    title: str = Field(..., description="Task title", max_length=255)
    description: str | None = Field(None, description="Task description")
    status: str = Field(default=TaskStatus.TODO, description="Task status")
    priority: str = Field(default=TaskPriority.MEDIUM, description="Task priority")
    assigned_to_id: UUID | None = Field(None, description="Assigned user ID")
    due_date: datetime | None = Field(None, description="Due date")
    related_entity_type: str | None = Field(None, description="Related entity type")
    related_entity_id: UUID | None = Field(None, description="Related entity ID")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class TaskCreate(TaskBase):
    """Schema for creating a task."""

    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    title: str | None = Field(None, description="Task title", max_length=255)
    description: str | None = Field(None, description="Task description")
    status: str | None = Field(None, description="Task status")
    priority: str | None = Field(None, description="Task priority")
    assigned_to_id: UUID | None = Field(None, description="Assigned user ID")
    due_date: datetime | None = Field(None, description="Due date")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class TaskResponse(TaskBase):
    """Schema for task response."""

    id: UUID
    tenant_id: UUID
    created_by_id: UUID | None
    workflow_id: UUID | None
    workflow_step_id: UUID | None
    parent_task_id: UUID | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="task_metadata", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TaskChecklistItemBase(BaseModel):
    """Base schema for checklist item."""

    title: str = Field(..., description="Item title", max_length=255)
    completed: bool = Field(default=False, description="Whether item is completed")
    order: int = Field(default=0, description="Item order")


class TaskChecklistItemCreate(TaskChecklistItemBase):
    """Schema for creating a checklist item."""

    pass


class TaskChecklistItemUpdate(BaseModel):
    """Schema for updating a checklist item."""

    title: str | None = Field(None, description="Item title", max_length=255)
    completed: bool | None = Field(None, description="Whether item is completed")
    order: int | None = Field(None, description="Item order")


class TaskChecklistItemResponse(TaskChecklistItemBase):
    """Schema for checklist item response."""

    id: UUID
    task_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowBase(BaseModel):
    """Base schema for workflow."""

    name: str = Field(..., description="Workflow name", max_length=255)
    description: str | None = Field(None, description="Workflow description")
    enabled: bool = Field(default=True, description="Whether workflow is enabled")
    definition: dict[str, Any] = Field(..., description="Workflow definition")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class WorkflowCreate(WorkflowBase):
    """Schema for creating a workflow."""

    pass


class WorkflowUpdate(BaseModel):
    """Schema for updating a workflow."""

    name: str | None = Field(None, description="Workflow name", max_length=255)
    description: str | None = Field(None, description="Workflow description")
    enabled: bool | None = Field(None, description="Whether workflow is enabled")
    definition: dict[str, Any] | None = Field(None, description="Workflow definition")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class WorkflowResponse(WorkflowBase):
    """Schema for workflow response."""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="workflow_metadata", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WorkflowStepBase(BaseModel):
    """Base schema for workflow step."""

    name: str = Field(..., description="Step name", max_length=255)
    step_type: str = Field(..., description="Step type", max_length=50)
    order: int = Field(..., description="Step order")
    config: dict[str, Any] | None = Field(None, description="Step configuration")
    transitions: list[dict] | None = Field(None, description="Step transitions")


class WorkflowStepCreate(WorkflowStepBase):
    """Schema for creating a workflow step."""

    workflow_id: UUID = Field(..., description="Workflow ID")


class WorkflowStepResponse(WorkflowStepBase):
    """Schema for workflow step response."""

    id: UUID
    workflow_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowExecutionBase(BaseModel):
    """Base schema for workflow execution."""

    entity_type: str | None = Field(None, description="Related entity type")
    entity_id: UUID | None = Field(None, description="Related entity ID")
    execution_data: dict[str, Any] | None = Field(None, description="Execution data")


class WorkflowExecutionCreate(WorkflowExecutionBase):
    """Schema for creating a workflow execution."""

    workflow_id: UUID = Field(..., description="Workflow ID")


class WorkflowExecutionResponse(WorkflowExecutionBase):
    """Schema for workflow execution response."""

    id: UUID
    workflow_id: UUID
    tenant_id: UUID
    status: str
    current_step_id: UUID | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)







