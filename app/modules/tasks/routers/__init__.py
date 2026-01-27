"""Task sub-routers for modular organization."""

# Import all routers for easy access
from app.modules.tasks.routers import (
    tasks_analytics,
    tasks_assignments,
    tasks_calendar,
    tasks_checklist,
    tasks_comments,
    tasks_core,
    tasks_dependencies,
    tasks_files,
    tasks_preferences,
    tasks_status,
    tasks_tags,
)

__all__ = [
    "tasks_analytics",
    "tasks_assignments", 
    "tasks_calendar",
    "tasks_checklist",
    "tasks_comments",
    "tasks_core",
    "tasks_dependencies",
    "tasks_files",
    "tasks_preferences",
    "tasks_status",
    "tasks_tags",
]
