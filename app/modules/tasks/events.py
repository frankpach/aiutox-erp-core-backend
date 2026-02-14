"""Task module domain events."""

from __future__ import annotations

TASK_CREATED = "task.created"
TASK_UPDATED = "task.updated"
TASK_COMPLETED = "task.completed"
TASK_ASSIGNED = "task.assigned"

PUBLISHED_EVENTS = [
    TASK_CREATED,
    TASK_UPDATED,
    TASK_COMPLETED,
    TASK_ASSIGNED,
]

CONSUMED_EVENTS = [
    "approval.requested",
]
