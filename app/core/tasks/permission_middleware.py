"""Permission middleware for Tasks module with granular checks."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.tasks.permissions import TaskPermission, TaskPermissionChecker
from app.models.task import Task
from app.models.user import User


def require_task_permission(permission: TaskPermission, task_id_param: str | None = None):
    """Dependency to check granular task permissions."""

    def permission_dependency(
        current_user: User,
        db: Session = Depends(get_db),
        task_id: UUID | None = None,
    ) -> User:
        """Check permission and return user if authorized."""

        # If task_id is provided in path parameters, get the task
        task = None
        if task_id_param and task_id:
            task = db.query(Task).filter(
                Task.id == task_id,
                Task.tenant_id == current_user.tenant_id
            ).first()

            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found"
                )

        # Check permission
        checker = TaskPermissionChecker(current_user, current_user.tenant_id)

        if task:
            # Task-specific permission check
            permission_methods = {
                TaskPermission.VIEW: checker.can_view_task,
                TaskPermission.UPDATE: checker.can_update_task,
                TaskPermission.DELETE: checker.can_delete_task,
                TaskPermission.ASSIGN: lambda t, **kwargs: checker.can_assign_task(t, kwargs.get('target_user_id')),
                TaskPermission.CHANGE_STATUS: lambda t, **kwargs: checker.can_change_task_status(t, kwargs.get('new_status', '')),
                TaskPermission.MARK_DONE: checker.can_mark_task_done,
                TaskPermission.REOPEN: checker.can_reopen_task,
                TaskPermission.CANCEL: checker.can_cancel_task,
            }

            method = permission_methods.get(permission)
            if method and not method(task):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions for {permission.value} on this task"
                )
        else:
            # General permission check
            if not checker.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: {permission.value}"
                )

        return current_user

    return permission_dependency


def require_task_view_permission(
    current_user: User,
    db: Session = Depends(get_db),
    task_id: UUID = None,
) -> User:
    """Check if user can view a specific task."""
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID is required"
        )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.tenant_id == current_user.tenant_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.can_view_task(task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view this task"
        )

    return current_user


def require_task_update_permission(
    current_user: User,
    db: Session = Depends(get_db),
    task_id: UUID = None,
) -> User:
    """Check if user can update a specific task."""
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID is required"
        )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.tenant_id == current_user.tenant_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.can_update_task(task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this task"
        )

    return current_user


def require_task_delete_permission(
    current_user: User,
    db: Session = Depends(get_db),
    task_id: UUID = None,
) -> User:
    """Check if user can delete a specific task."""
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID is required"
        )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.tenant_id == current_user.tenant_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.can_delete_task(task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this task"
        )

    return current_user


def require_task_assign_permission(
    current_user: User,
    db: Session = Depends(get_db),
    task_id: UUID = None,
) -> User:
    """Check if user can assign a specific task."""
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID is required"
        )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.tenant_id == current_user.tenant_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.has_permission(TaskPermission.ASSIGN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to assign tasks"
        )

    return current_user


def require_agenda_view_permission(current_user: User) -> User:
    """Check if user can view agenda."""
    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.can_view_agenda():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view agenda"
        )

    return current_user


def require_agenda_manage_permission(current_user: User) -> User:
    """Check if user can manage agenda."""
    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.can_manage_agenda():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage agenda"
        )

    return current_user


def require_calendar_sources_permission(current_user: User) -> User:
    """Check if user can view calendar sources."""
    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.has_permission(TaskPermission.CALENDAR_SOURCES_VIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view calendar sources"
        )

    return current_user


def require_calendar_sources_manage_permission(current_user: User) -> User:
    """Check if user can manage calendar sources."""
    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.has_permission(TaskPermission.CALENDAR_SOURCES_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage calendar sources"
        )

    return current_user


def require_checklist_permission(
    current_user: User,
    db: Session = Depends(get_db),
    task_id: UUID = None,
) -> User:
    """Check if user can manage checklist for a specific task."""
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID is required"
        )

    task = db.query(Task).filter(
        Task.id == task_id,
        Task.tenant_id == current_user.tenant_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    checker = TaskPermissionChecker(current_user, current_user.tenant_id)
    if not checker.can_manage_checklist(task):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage checklist for this task"
        )

    return current_user


# Type annotations for use in FastAPI dependencies
TaskViewUser = Annotated[User, Depends(require_task_view_permission)]
TaskUpdateUser = Annotated[User, Depends(require_task_update_permission)]
TaskDeleteUser = Annotated[User, Depends(require_task_delete_permission)]
TaskAssignUser = Annotated[User, Depends(require_task_assign_permission)]
AgendaViewUser = Annotated[User, Depends(require_agenda_view_permission)]
AgendaManageUser = Annotated[User, Depends(require_agenda_manage_permission)]
CalendarSourcesUser = Annotated[User, Depends(require_calendar_sources_permission)]
CalendarSourcesManageUser = Annotated[User, Depends(require_calendar_sources_manage_permission)]
ChecklistUser = Annotated[User, Depends(require_checklist_permission)]
