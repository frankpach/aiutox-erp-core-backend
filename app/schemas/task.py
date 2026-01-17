"""Task schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.task import (
    TaskPriority,
    TaskRecurrenceFrequency,
    TaskReminderType,
    TaskStatus,
)


class TaskBase(BaseModel):
    """Base schema for task."""

    title: str = Field(..., description="Task title", max_length=255)
    description: str | None = Field(None, description="Task description")
    status: str = Field(default=TaskStatus.TODO, description="Task status")
    priority: str = Field(default=TaskPriority.MEDIUM, description="Task priority")
    assigned_to_id: UUID | None = Field(None, description="Assigned user ID (legacy, use assignments)")
    due_date: datetime | None = Field(None, description="Due date")
    start_at: datetime | None = Field(None, description="Start datetime")
    end_at: datetime | None = Field(None, description="End datetime")
    all_day: bool = Field(default=False, description="All day task")
    tag_ids: list[UUID] | None = Field(None, description="Core tag IDs")
    color_override: str | None = Field(None, description="Manual color override (hex)")
    related_entity_type: str | None = Field(None, description="Related entity type (legacy)")
    related_entity_id: UUID | None = Field(None, description="Related entity ID (legacy)")
    source_module: str | None = Field(None, description="Source module (e.g., 'projects', 'workflows')")
    source_id: UUID | None = Field(None, description="Source entity ID")
    source_context: dict[str, Any] | None = Field(None, description="Additional context from source module")
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
    start_at: datetime | None = Field(None, description="Start datetime")
    end_at: datetime | None = Field(None, description="End datetime")
    all_day: bool | None = Field(None, description="All day task")
    tag_ids: list[UUID] | None = Field(None, description="Core tag IDs")
    color_override: str | None = Field(None, description="Manual color override (hex)")
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
    checklist: list[TaskChecklistItemResponse] | None = Field(default=[], description="Task checklist items")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TaskModuleSettings(BaseModel):
    """Schema for Tasks module settings."""

    calendar_enabled: bool = Field(default=True, description="Whether calendar is enabled")
    board_enabled: bool = Field(default=True, description="Whether board view is enabled")
    inbox_enabled: bool = Field(default=True, description="Whether inbox view is enabled")
    list_enabled: bool = Field(default=True, description="Whether list view is enabled")
    stats_enabled: bool = Field(default=True, description="Whether stats view is enabled")


class TaskModuleSettingsUpdate(BaseModel):
    """Schema for updating Tasks module settings."""

    calendar_enabled: bool | None = Field(None, description="Whether calendar is enabled")
    board_enabled: bool | None = Field(None, description="Whether board view is enabled")
    inbox_enabled: bool | None = Field(None, description="Whether inbox view is enabled")
    list_enabled: bool | None = Field(None, description="Whether list view is enabled")
    stats_enabled: bool | None = Field(None, description="Whether stats view is enabled")


class TaskAssignmentBase(BaseModel):
    """Base schema for task assignment."""

    task_id: UUID = Field(..., description="Task ID")
    assigned_to_id: UUID | None = Field(None, description="User ID to assign to")
    assigned_to_group_id: UUID | None = Field(None, description="Group ID to assign to")
    role: str | None = Field(None, description="Assignment role (e.g., 'owner', 'reviewer')")
    notes: str | None = Field(None, description="Assignment notes")
    created_by_id: UUID = Field(..., description="User ID who created the assignment")
    updated_by_id: UUID | None = Field(None, description="User ID who last updated the assignment")


class TaskAssignmentCreate(TaskAssignmentBase):
    """Schema for creating a task assignment."""

    @model_validator(mode='after')
    def validate_exclusive_assignment(self) -> TaskAssignmentCreate:
        """Validar que solo se asigne a usuario O grupo, no ambos."""
        if not self.assigned_to_id and not self.assigned_to_group_id:
            raise ValueError("Debe asignar a un usuario o grupo")
        if self.assigned_to_id and self.assigned_to_group_id:
            raise ValueError("No puede asignar a usuario y grupo simultáneamente")
        return self


class TaskAssignmentResponse(TaskAssignmentBase):
    """Schema for task assignment response."""

    id: UUID
    tenant_id: UUID
    assigned_by_id: UUID | None
    assigned_at: datetime
    created_by_id: UUID
    updated_by_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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


class TaskReminderBase(BaseModel):
    """Base schema for task reminder."""

    reminder_type: str = Field(default=TaskReminderType.IN_APP, description="Reminder type")
    reminder_time: datetime = Field(..., description="When to send reminder")
    message: str | None = Field(None, description="Reminder message")


class TaskReminderCreate(TaskReminderBase):
    """Schema for creating a task reminder."""

    task_id: UUID = Field(..., description="Task ID")


class TaskReminderUpdate(BaseModel):
    """Schema for updating a task reminder."""

    reminder_type: str | None = Field(None, description="Reminder type")
    reminder_time: datetime | None = Field(None, description="When to send reminder")
    message: str | None = Field(None, description="Reminder message")
    sent: bool | None = Field(None, description="Whether reminder has been sent")


class TaskReminderResponse(TaskReminderBase):
    """Schema for task reminder response."""

    id: UUID
    task_id: UUID
    tenant_id: UUID
    sent: bool
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskRecurrenceBase(BaseModel):
    """Base schema for task recurrence."""

    frequency: str = Field(default=TaskRecurrenceFrequency.WEEKLY, description="Recurrence frequency")
    interval: int = Field(default=1, description="Interval (e.g., every 2 weeks)")
    start_date: datetime = Field(..., description="Start date of recurrence")
    end_date: datetime | None = Field(None, description="End date of recurrence")
    max_occurrences: int | None = Field(None, description="Maximum number of occurrences")
    days_of_week: list[int] | None = Field(None, description="Days of week for weekly recurrence (0=Monday)")
    day_of_month: int | None = Field(None, description="Day of month for monthly recurrence (1-31)")
    custom_config: dict[str, Any] | None = Field(None, description="Custom recurrence configuration")
    active: bool = Field(default=True, description="Whether recurrence is active")


class TaskRecurrenceCreate(TaskRecurrenceBase):
    """Schema for creating a task recurrence."""

    task_id: UUID = Field(..., description="Task ID")


class TaskRecurrenceUpdate(BaseModel):
    """Schema for updating a task recurrence."""

    frequency: str | None = Field(None, description="Recurrence frequency")
    interval: int | None = Field(None, description="Interval")
    start_date: datetime | None = Field(None, description="Start date of recurrence")
    end_date: datetime | None = Field(None, description="End date of recurrence")
    max_occurrences: int | None = Field(None, description="Maximum number of occurrences")
    current_occurrence: int | None = Field(None, description="Current occurrence count")
    days_of_week: list[int] | None = Field(None, description="Days of week")
    day_of_month: int | None = Field(None, description="Day of month")
    custom_config: dict[str, Any] | None = Field(None, description="Custom configuration")
    active: bool | None = Field(None, description="Whether recurrence is active")


class TaskRecurrenceResponse(TaskRecurrenceBase):
    """Schema for task recurrence response."""

    id: UUID
    task_id: UUID
    tenant_id: UUID
    current_occurrence: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)




