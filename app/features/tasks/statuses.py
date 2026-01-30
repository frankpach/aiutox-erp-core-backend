"""
Task Statuses module - Custom status management for tasks
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from ...api.deps import get_current_user
from ...core.db.deps import get_db
from ...core.exceptions import APIException
from ...models.task_status import TaskStatus
from ...models.user import User

router = APIRouter(tags=["task-statuses"])


# Pydantic Schemas
class TaskStatusBase(BaseModel):
    name: str = Field(..., max_length=50, description="Status name")
    color: str = Field(default="#6b7280", description="Hex color code")
    type: str = Field(default="open", description="Status type: open, in_progress, on_hold, completed, canceled")
    order: int = Field(default=0, description="Display order")
    is_system: bool = Field(default=False, description="System status (non-editable)")


class TaskStatusCreate(BaseModel):
    name: str = Field(..., max_length=50)
    color: str = Field(default="#6b7280")
    type: str = Field(default="open")
    order: int = Field(default=0)


class TaskStatusUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    color: str | None = None
    type: str | None = None
    order: int | None = None


class TaskStatusResponse(TaskStatusBase):
    id: str
    tenant_id: str
    is_system: bool

    model_config = ConfigDict(from_attributes=True)

    @field_validator('id', 'tenant_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        return str(v) if v else None


# API Endpoints
@router.get("/", response_model=list[TaskStatusResponse])
async def get_task_statuses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_system: bool = False,
):
    """Get all task statuses for current tenant"""
    query = db.query(TaskStatus).filter(TaskStatus.tenant_id == current_user.tenant_id)

    if not include_system:
        query = query.filter(TaskStatus.is_system is False)

    statuses = query.order_by(TaskStatus.order, TaskStatus.id).all()
    return statuses


@router.post("/", response_model=TaskStatusResponse)
async def create_task_status(
    status_data: TaskStatusCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task status"""
    # Check if status name already exists for this tenant
    existing = db.query(TaskStatus).filter(
        TaskStatus.tenant_id == current_user.tenant_id,
        TaskStatus.name == status_data.name
    ).first()

    if existing:
        raise APIException(
            code="STATUS_ALREADY_EXISTS",
            message=f"Status '{status_data.name}' already exists",
            status_code=400
        )

    status = TaskStatus(
        tenant_id=current_user.tenant_id,
        **status_data.model_dump(),
        is_system=False  # User-created statuses are never system
    )

    db.add(status)
    db.commit()
    db.refresh(status)

    return status


@router.put("/{status_id}", response_model=TaskStatusResponse)
async def update_task_status(
    status_id: str,
    status_data: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a task status"""
    status = db.query(TaskStatus).filter(
        TaskStatus.id == status_id,
        TaskStatus.tenant_id == current_user.tenant_id
    ).first()

    if not status:
        raise APIException(
            code="STATUS_NOT_FOUND",
            message="Status not found",
            status_code=404
        )

    if status.is_system:
        raise APIException(
            code="SYSTEM_STATUS_READONLY",
            message="System statuses cannot be modified",
            status_code=403
        )

    # Update fields
    for field, value in status_data.model_dump(exclude_unset=True).items():
        setattr(status, field, value)

    db.commit()
    db.refresh(status)

    return status


@router.delete("/{status_id}")
async def delete_task_status(
    status_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a task status"""
    status = db.query(TaskStatus).filter(
        TaskStatus.id == status_id,
        TaskStatus.tenant_id == current_user.tenant_id
    ).first()

    if not status:
        raise APIException(
            code="STATUS_NOT_FOUND",
            message="Status not found",
            status_code=404
        )

    if status.is_system:
        raise APIException(
            code="SYSTEM_STATUS_READONLY",
            message="System statuses cannot be deleted",
            status_code=403
        )

    # Check if status is being used by tasks
    from ...models.task import Task
    tasks_using_status = db.query(Task).filter(
        Task.status_id == status_id,
        Task.tenant_id == current_user.tenant_id
    ).count()

    if tasks_using_status > 0:
        raise APIException(
            code="STATUS_IN_USE",
            detail=f"Cannot delete status: {tasks_using_status} tasks are using this status",
            status_code=400
        )

    # Hard delete (remove from database)
    db.delete(status)
    db.commit()

    return {"message": "Status deleted successfully"}


@router.patch("/{status_id}/reorder")
async def reorder_task_statuses(
    status_id: str,
    new_order: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reorder task statuses"""
    status = db.query(TaskStatus).filter(
        TaskStatus.id == status_id,
        TaskStatus.tenant_id == current_user.tenant_id
    ).first()

    if not status:
        raise APIException(
            code="STATUS_NOT_FOUND",
            message="Status not found",
            status_code=404
        )

    if status.is_system:
        raise APIException(
            code="SYSTEM_STATUS_READONLY",
            message="System statuses cannot be reordered",
            status_code=403
        )

    # Get all statuses for this tenant (excluding system)
    all_statuses = db.query(TaskStatus).filter(
        TaskStatus.tenant_id == current_user.tenant_id,
        TaskStatus.is_system is False
    ).order_by(TaskStatus.order).all()

    # Reorder logic
    if new_order < status.order:
        # Move up: shift others down
        for s in all_statuses:
            if s.order >= new_order and s.order < status.order:
                s.order += 1
    else:
        # Move down: shift others up
        for s in all_statuses:
            if s.order > status.order and s.order <= new_order:
                s.order -= 1

    status.order = new_order
    status.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Status reordered successfully"}


# Initialize default system statuses
async def initialize_system_statuses(db: Session, tenant_id: str):
    """Initialize default system statuses for a tenant"""
    default_statuses = [
        {
            "name": "Por Hacer",
            "color": "#6b7280",
            "type": "open",
            "order": 0,
            "is_system": True
        },
        {
            "name": "En Progreso",
            "color": "#3b82f6",
            "type": "in_progress",
            "order": 1,
            "is_system": True
        },
        {
            "name": "En Espera",
            "color": "#f59e0b",
            "type": "on_hold",
            "order": 2,
            "is_system": True
        },
        {
            "name": "Completado",
            "color": "#22c55e",
            "type": "completed",
            "order": 3,
            "is_system": True
        },
        {
            "name": "Cancelado",
            "color": "#ef4444",
            "type": "canceled",
            "order": 4,
            "is_system": True
        }
    ]

    for status_data in default_statuses:
        existing = db.query(TaskStatus).filter(
            TaskStatus.tenant_id == tenant_id,
            TaskStatus.name == status_data["name"]
        ).first()

        if not existing:
            status = TaskStatus(
                tenant_id=tenant_id,
                **status_data
            )
            db.add(status)

    db.commit()
