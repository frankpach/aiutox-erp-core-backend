"""
Payloads estándar para eventos pub/sub.

Define los schemas Pydantic para los payloads de eventos.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================
# TASKS
# ============================================


class TaskEventPayload(BaseModel):
    """Payload genérico para eventos de tareas"""

    task_id: UUID
    tenant_id: UUID
    event_type: str
    data: dict[str, Any] | None = None
    user_id: UUID | None = None
    timestamp: str | None = None


class TaskCreatedPayload(BaseModel):
    """Payload para evento tasks.created"""

    task_id: UUID
    tenant_id: UUID
    title: str
    status: str
    priority: str
    created_by_id: UUID
    assigned_user_ids: list[UUID] = Field(default_factory=list)
    assigned_group_ids: list[UUID] = Field(default_factory=list)
    source_module: str | None = None
    source_id: UUID | None = None
    source_context: dict[str, Any] | None = None
    template_id: UUID | None = None


class TaskUpdatedPayload(BaseModel):
    """Payload para evento tasks.updated"""

    task_id: UUID
    tenant_id: UUID
    changes: dict[str, Any]
    updated_by_id: UUID


class TaskMovedPayload(BaseModel):
    """Payload para evento tasks.moved (Board)"""

    task_id: UUID
    tenant_id: UUID
    old_status_id: UUID | None
    new_status_id: UUID
    old_priority: str | None
    new_priority: str | None
    board_order: int


class TaskCreateRequestPayload(BaseModel):
    """Payload para solicitud de creación de tarea desde otro módulo"""

    title: str
    description: str | None = None
    priority: str = "medium"
    status: str = "todo"
    due_date: str | None = None
    assigned_user_ids: list[UUID] = Field(default_factory=list)
    assigned_group_ids: list[UUID] = Field(default_factory=list)
    source_module: str
    source_id: UUID
    source_context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    template_id: UUID | None = None


class TaskDependencyCreatedPayload(BaseModel):
    """Payload para evento task_dependency.created"""

    parent_task_id: UUID
    child_task_id: UUID
    dependency_type: str
    tenant_id: UUID


# ============================================
# CALENDAR
# ============================================


class CalendarEventCreatedPayload(BaseModel):
    """Payload para evento calendar.event.created"""

    event_id: UUID
    tenant_id: UUID
    calendar_id: UUID
    title: str
    start_time: str
    end_time: str
    organizer_id: UUID
    source_type: str | None = None
    source_id: UUID | None = None
    is_recurring: bool = False


class CalendarEventUpdatedPayload(BaseModel):
    """Payload para evento calendar.event.updated"""

    event_id: UUID
    tenant_id: UUID
    changes: dict[str, Any]
    updated_by_id: UUID


class CalendarSharedPayload(BaseModel):
    """Payload para evento calendar.shared"""

    calendar_id: UUID
    tenant_id: UUID
    shared_with_user_id: UUID | None = None
    shared_with_team_id: UUID | None = None
    permission_level: str
    shared_by_user_id: UUID


# ============================================
# NOTIFICATIONS
# ============================================


class NotificationSendPayload(BaseModel):
    """Payload para envío de notificaciones"""

    user_id: UUID
    title: str
    message: str
    notification_type: str
    metadata: dict[str, Any] | None = None
    priority: str = "normal"
    action_url: str | None = None


# ============================================
# APPROVALS
# ============================================


class ApprovalStatusChangedPayload(BaseModel):
    """Payload para evento approvals.status_changed"""

    approval_id: UUID
    tenant_id: UUID
    status: str
    previous_status: str
    changed_by_id: UUID
    comments: str | None = None


# ============================================
# WORKFLOWS
# ============================================


class WorkflowStepCompletedPayload(BaseModel):
    """Payload para evento workflows.step_completed"""

    workflow_id: UUID
    step_id: UUID
    tenant_id: UUID
    completed_by_id: UUID
    output_data: dict[str, Any] | None = None


# ============================================
# SCHEDULER
# ============================================


class SchedulerEventScheduledPayload(BaseModel):
    """Payload para evento scheduler.event_scheduled"""

    event_id: UUID
    resource_id: UUID
    tenant_id: UUID
    start_time: str
    end_time: str
    scheduled_by_id: UUID


# ============================================
# AUTOMATION
# ============================================


class AutomationTriggeredPayload(BaseModel):
    """Payload para evento automation.triggered"""

    automation_id: UUID
    tenant_id: UUID
    trigger_type: str
    trigger_context: dict[str, Any]
    triggered_at: str
