"""Granular permissions system for Tasks module."""

from enum import Enum
from uuid import UUID

from app.models.task import Task
from app.models.user import User


class TaskPermission(str, Enum):
    """Task-specific permissions."""

    # Basic permissions
    VIEW = "tasks.view"
    CREATE = "tasks.create"
    MANAGE = "tasks.manage"
    UPDATE = "tasks.update"
    DELETE = "tasks.delete"

    # Assignment permissions
    ASSIGN = "tasks.assign"
    ASSIGN_SELF = "tasks.assign.self"
    ASSIGN_OTHERS = "tasks.assign.others"
    UNASSIGN = "tasks.unassign"

    # Status permissions
    CHANGE_STATUS = "tasks.status.change"
    CHANGE_STATUS_SELF = "tasks.status.change.self"
    CHANGE_STATUS_OTHERS = "tasks.status.change.others"
    MARK_DONE = "tasks.status.done"
    REOPEN = "tasks.status.reopen"
    CANCEL = "tasks.status.cancel"

    # Agenda/Calendar permissions
    AGENDA_VIEW = "tasks.agenda.view"
    AGENDA_MANAGE = "tasks.agenda.manage"
    CALENDAR_SOURCES_VIEW = "tasks.calendar_sources.view"
    CALENDAR_SOURCES_MANAGE = "tasks.calendar_sources.manage"

    # Checklist permissions
    CHECKLIST_CREATE = "tasks.checklist.create"
    CHECKLIST_UPDATE = "tasks.checklist.update"
    CHECKLIST_DELETE = "tasks.checklist.delete"

    # Reminder permissions
    REMINDERS_CREATE = "tasks.reminders.create"
    REMINDERS_UPDATE = "tasks.reminders.update"
    REMINDERS_DELETE = "tasks.reminders.delete"

    # Bulk operations
    BULK_UPDATE = "tasks.bulk.update"
    BULK_DELETE = "tasks.bulk.delete"
    BULK_ASSIGN = "tasks.bulk.assign"

    # Admin permissions
    ADMIN = "tasks.admin"
    VIEW_ALL = "tasks.view.all"
    MANAGE_ALL = "tasks.manage.all"


class TaskPermissionChecker:
    """Granular permission checker for task operations."""

    def __init__(self, user: User, tenant_id: UUID):
        """Initialize permission checker with user context."""
        self.user = user
        self.tenant_id = tenant_id
        self.user_permissions = self._get_user_permissions()
        self.user_roles = self._get_user_roles()

    def _get_user_permissions(self) -> set[str]:
        """Get user's direct permissions."""
        permissions = set()

        # Add permissions based on user roles
        if "admin" in self.user_roles:
            permissions.update([perm.value for perm in TaskPermission])
        elif "manager" in self.user_roles:
            permissions.update([
                TaskPermission.VIEW,
                TaskPermission.CREATE,
                TaskPermission.MANAGE,
                TaskPermission.UPDATE,
                TaskPermission.ASSIGN,
                TaskPermission.ASSIGN_OTHERS,
                TaskPermission.CHANGE_STATUS,
                TaskPermission.CHANGE_STATUS_OTHERS,
                TaskPermission.MARK_DONE,
                TaskPermission.REOPEN,
                TaskPermission.AGENDA_VIEW,
                TaskPermission.CALENDAR_SOURCES_VIEW,
                TaskPermission.CHECKLIST_CREATE,
                TaskPermission.CHECKLIST_UPDATE,
                TaskPermission.REMINDERS_CREATE,
                TaskPermission.BULK_UPDATE,
                TaskPermission.VIEW_ALL,
            ])
        elif "employee" in self.user_roles:
            permissions.update([
                TaskPermission.VIEW,
                TaskPermission.CREATE,
                TaskPermission.MANAGE,
                TaskPermission.UPDATE,
                TaskPermission.ASSIGN_SELF,
                TaskPermission.CHANGE_STATUS_SELF,
                TaskPermission.MARK_DONE,
                TaskPermission.REOPEN,
                TaskPermission.AGENDA_VIEW,
                TaskPermission.CALENDAR_SOURCES_VIEW,
                TaskPermission.CHECKLIST_CREATE,
                TaskPermission.CHECKLIST_UPDATE,
                TaskPermission.REMINDERS_CREATE,
            ])

        return permissions

    def _get_user_roles(self) -> set[str]:
        """Get user's roles."""
        roles = set()

        # Add roles based on user properties
        if self.user.is_superuser:
            roles.add("admin")
        elif hasattr(self.user, 'role') and self.user.role:
            roles.add(self.user.role.lower())

        return roles

    def has_permission(self, permission: TaskPermission | str) -> bool:
        """Check if user has a specific permission."""
        perm_value = permission.value if isinstance(permission, TaskPermission) else permission
        return perm_value in self.user_permissions

    def can_view_task(self, task: Task) -> bool:
        """Check if user can view a specific task."""
        # Admin can view all tasks
        if self.has_permission(TaskPermission.VIEW_ALL):
            return True

        # Basic view permission
        if not self.has_permission(TaskPermission.VIEW):
            return False

        # User can view their own tasks
        if task.created_by_id == self.user.id:
            return True

        # User can view tasks assigned to them
        if task.assigned_to_id == self.user.id:
            return True

        # Check modern assignments
        if hasattr(task, 'assignments') and task.assignments:
            for assignment in task.assignments:
                if assignment.assigned_to_id == self.user.id:
                    return True

        return False

    def can_create_task(self) -> bool:
        """Check if user can create tasks."""
        return self.has_permission(TaskPermission.CREATE)

    def can_update_task(self, task: Task) -> bool:
        """Check if user can update a specific task."""
        # Admin can update all tasks
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # Basic update permission
        if not self.has_permission(TaskPermission.UPDATE):
            return False

        # User can update their own tasks
        if task.created_by_id == self.user.id:
            return True

        # User can update tasks assigned to them
        if task.assigned_to_id == self.user.id:
            return True

        # Check modern assignments
        if hasattr(task, 'assignments') and task.assignments:
            for assignment in task.assignments:
                if assignment.assigned_to_id == self.user.id:
                    return True

        return False

    def can_delete_task(self, task: Task) -> bool:
        """Check if user can delete a specific task."""
        # Admin can delete all tasks
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # Basic delete permission
        if not self.has_permission(TaskPermission.DELETE):
            return False

        # Only task creators can delete their own tasks (more restrictive)
        return task.created_by_id == self.user.id

    def can_assign_task(self, task: Task, target_user_id: UUID) -> bool:
        """Check if user can assign a task to a specific user."""
        # Admin can assign any task to anyone
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # Basic assign permission
        if not self.has_permission(TaskPermission.ASSIGN):
            return False

        # Check if assigning to self
        if target_user_id == self.user.id:
            return self.has_permission(TaskPermission.ASSIGN_SELF)

        # Check if assigning to others
        return self.has_permission(TaskPermission.ASSIGN_OTHERS)

    def can_change_task_status(self, task: Task, new_status: str) -> bool:
        """Check if user can change task status to a specific value."""
        # Admin can change any status
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # Basic status change permission
        if not self.has_permission(TaskPermission.CHANGE_STATUS):
            return False

        # Check if changing own task
        is_own_task = (
            task.created_by_id == self.user.id or
            task.assigned_to_id == self.user.id
        )

        if is_own_task:
            return self.has_permission(TaskPermission.CHANGE_STATUS_SELF)

        # Check if changing others' tasks
        return self.has_permission(TaskPermission.CHANGE_STATUS_OTHERS)

    def can_mark_task_done(self, task: Task) -> bool:
        """Check if user can mark task as done."""
        # Admin can mark any task as done
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # Basic permission
        if not self.has_permission(TaskPermission.MARK_DONE):
            return False

        # User can mark their own assigned tasks as done
        return (
            task.assigned_to_id == self.user.id or
            task.created_by_id == self.user.id
        )

    def can_reopen_task(self, task: Task) -> bool:
        """Check if user can reopen a completed task."""
        # Admin can reopen any task
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # Basic permission
        if not self.has_permission(TaskPermission.REOPEN):
            return False

        # Only task creators can reopen their own tasks
        return task.created_by_id == self.user.id

    def can_cancel_task(self, task: Task) -> bool:
        """Check if user can cancel a task."""
        # Admin can cancel any task
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # Basic permission
        if not self.has_permission(TaskPermission.CANCEL):
            return False

        # Only task creators can cancel their own tasks
        return task.created_by_id == self.user.id

    def can_view_agenda(self) -> bool:
        """Check if user can view agenda."""
        return self.has_permission(TaskPermission.AGENDA_VIEW)

    def can_manage_agenda(self) -> bool:
        """Check if user can manage agenda."""
        return self.has_permission(TaskPermission.AGENDA_MANAGE)

    def can_manage_checklist(self, task: Task) -> bool:
        """Check if user can manage task checklist."""
        # Admin can manage any checklist
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # User can manage checklist of their own tasks
        return (
            task.created_by_id == self.user.id or
            task.assigned_to_id == self.user.id
        )

    def can_bulk_update_tasks(self, task_ids: list[UUID]) -> bool:
        """Check if user can bulk update specific tasks."""
        if not self.has_permission(TaskPermission.BULK_UPDATE):
            return False

        # Admin can bulk update any tasks
        if self.has_permission(TaskPermission.MANAGE_ALL):
            return True

        # For non-admins, we would need to check each task
        # This is a simplified check - in production, you'd verify each task
        return True

    def get_visible_task_filter(self) -> dict[str, any]:
        """Get filter conditions for visible tasks based on permissions."""
        if self.has_permission(TaskPermission.VIEW_ALL):
            return {}  # No filter - can see all tasks

        # Basic visibility filter for regular users
        return {
            "or": [
                {"created_by_id": self.user.id},
                {"assigned_to_id": self.user.id},
                # TODO: Add modern assignments filter
                # TODO: Add group assignments filter
            ]
        }

    def audit_permission_check(
        self,
        permission: TaskPermission | str,
        resource_id: UUID | None = None,
        details: dict | None = None
    ) -> bool:
        """Check permission and log for audit purposes."""
        has_perm = self.has_permission(permission)

        # Log permission check for audit
        # TODO: Integrate with audit service

        return has_perm


def check_task_permission(
    user: User,
    tenant_id: UUID,
    permission: TaskPermission | str,
    task: Task | None = None,
    **kwargs
) -> bool:
    """Convenience function to check task permissions."""
    checker = TaskPermissionChecker(user, tenant_id)

    # Map permission strings to checker methods
    permission_methods = {
        TaskPermission.VIEW: checker.can_view_task,
        TaskPermission.CREATE: checker.can_create_task,
        TaskPermission.UPDATE: checker.can_update_task,
        TaskPermission.DELETE: checker.can_delete_task,
        TaskPermission.ASSIGN: checker.can_assign_task,
        TaskPermission.CHANGE_STATUS: checker.can_change_task_status,
        TaskPermission.MARK_DONE: checker.can_mark_task_done,
        TaskPermission.REOPEN: checker.can_reopen_task,
        TaskPermission.CANCEL: checker.can_cancel_task,
        TaskPermission.AGENDA_VIEW: checker.can_view_agenda,
        TaskPermission.AGENDA_MANAGE: checker.can_manage_agenda,
    }

    if isinstance(permission, str):
        try:
            permission = TaskPermission(permission)
        except ValueError:
            return False

    method = permission_methods.get(permission)
    if method:
        if task is not None:
            return method(task, **kwargs)
        else:
            return method(**kwargs)

    # Fallback to basic permission check
    return checker.has_permission(permission)
