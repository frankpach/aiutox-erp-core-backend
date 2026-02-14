"""RBAC permissions for tasks module."""

from __future__ import annotations

TASKS_VIEW = "tasks.view"
TASKS_MANAGE = "tasks.manage"
TASKS_CREATE = "tasks.create"
TASKS_UPDATE = "tasks.update"
TASKS_DELETE = "tasks.delete"
TASKS_ASSIGN = "tasks.assign"
TASKS_COMPLETE = "tasks.complete"

TASKS_PERMISSIONS = [
    TASKS_VIEW,
    TASKS_MANAGE,
    TASKS_CREATE,
    TASKS_UPDATE,
    TASKS_DELETE,
    TASKS_ASSIGN,
    TASKS_COMPLETE,
]
