"""Tasks router for task management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db.deps import get_db
from app.core.tasks.service import TaskService

# Import modular routers
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
from app.schemas.task import (
    TaskModuleSettings,
)

logger = logging.getLogger(__name__)

# Main router
router = APIRouter()

def get_task_service(db: Annotated[Session, Depends(get_db)]) -> TaskService:
    """Dependency to get TaskService."""
    return TaskService(db)

# Include all modular routers
router.include_router(tasks_status.router, tags=["tasks-status"])
router.include_router(tasks_core.router, tags=["tasks"])
router.include_router(tasks_checklist.router, tags=["tasks-checklist"])
router.include_router(tasks_assignments.router, tags=["tasks-assignments"])
router.include_router(tasks_calendar.router, tags=["tasks-calendar"])
router.include_router(tasks_files.router, tags=["tasks-files"])
router.include_router(tasks_comments.router, tags=["tasks-comments"])
router.include_router(tasks_tags.router, tags=["tasks-tags"])
router.include_router(tasks_analytics.router, tags=["tasks-analytics"])
router.include_router(tasks_dependencies.router, tags=["tasks-dependencies"])
router.include_router(tasks_preferences.router, tags=["tasks-preferences"])

# Legacy endpoints that haven't been migrated yet
TASK_SETTINGS_KEYS = {
    "calendar_enabled": "calendar.enabled",
    "board_enabled": "board.enabled",
    "inbox_enabled": "inbox.enabled",
    "list_enabled": "list.enabled",
    "gantt_enabled": "gantt.enabled",
    "calendar_auto_sync": "calendar.auto_sync",
    "default_priority": "tasks.default_priority",
    "default_status": "tasks.default_status",
    "task_auto_numbering": "tasks.auto_numbering",
    "task_number_prefix": "tasks.number_prefix",
    "task_number_separator": "tasks.number_separator",
    "allow_task_dependencies": "tasks.allow_dependencies",
    "require_dependency_resolution": "tasks.require_dependency_resolution",
    "max_task_depth": "tasks.max_depth",
    "enable_task_templates": "tasks.enable_templates",
    "default_task_duration": "tasks.default_duration",
    "enable_task_reminders": "tasks.enable_reminders",
    "default_reminder_time": "tasks.default_reminder_time",
    "enable_task_comments": "tasks.enable_comments",
    "enable_task_files": "tasks.enable_files",
    "max_file_size": "tasks.max_file_size",
    "allowed_file_types": "tasks.allowed_file_types",
    "enable_task_tags": "tasks.enable_tags",
    "max_tags_per_task": "tasks.max_tags_per_task",
    "enable_task_checklist": "tasks.enable_checklist",
    "max_checklist_items": "tasks.max_checklist_items",
    "enable_task_assignments": "tasks.enable_assignments",
    "max_assignees_per_task": "tasks.max_assignees_per_task",
    "enable_task_history": "tasks.enable_history",
    "history_retention_days": "tasks.history_retention_days",
}


def _build_task_settings(settings: dict) -> TaskModuleSettings:
    """Build task module settings from configuration."""
    return TaskModuleSettings(
        calendar_enabled=settings.get(TASK_SETTINGS_KEYS["calendar_enabled"], False),
        board_enabled=settings.get(TASK_SETTINGS_KEYS["board_enabled"], False),
        inbox_enabled=settings.get(TASK_SETTINGS_KEYS["inbox_enabled"], False),
        list_enabled=settings.get(TASK_SETTINGS_KEYS["list_enabled"], False),
        gantt_enabled=settings.get(TASK_SETTINGS_KEYS["gantt_enabled"], False),
        calendar_auto_sync=settings.get(TASK_SETTINGS_KEYS["calendar_auto_sync"], False),
        default_priority=settings.get(TASK_SETTINGS_KEYS["default_priority"], "medium"),
        default_status=settings.get(TASK_SETTINGS_KEYS["default_status"], "todo"),
        task_auto_numbering=settings.get(TASK_SETTINGS_KEYS["task_auto_numbering"], False),
        task_number_prefix=settings.get(TASK_SETTINGS_KEYS["task_number_prefix"], "TASK-"),
        task_number_separator=settings.get(TASK_SETTINGS_KEYS["task_number_separator"], "-"),
        allow_task_dependencies=settings.get(TASK_SETTINGS_KEYS["allow_task_dependencies"], True),
        require_dependency_resolution=settings.get(TASK_SETTINGS_KEYS["require_dependency_resolution"], False),
        max_task_depth=settings.get(TASK_SETTINGS_KEYS["max_task_depth"], 5),
        enable_task_templates=settings.get(TASK_SETTINGS_KEYS["enable_task_templates"], False),
        default_task_duration=settings.get(TASK_SETTINGS_KEYS["default_task_duration"], 60),
        enable_task_reminders=settings.get(TASK_SETTINGS_KEYS["enable_task_reminders"], True),
        default_reminder_time=settings.get(TASK_SETTINGS_KEYS["default_reminder_time"], 15),
        enable_task_comments=settings.get(TASK_SETTINGS_KEYS["enable_task_comments"], True),
        enable_task_files=settings.get(TASK_SETTINGS_KEYS["enable_task_files"], True),
        max_file_size=settings.get(TASK_SETTINGS_KEYS["max_file_size"], 10485760),  # 10MB
        allowed_file_types=settings.get(TASK_SETTINGS_KEYS["allowed_file_types"], [".pdf", ".doc", ".docx", ".txt", ".jpg", ".png"]),
        enable_task_tags=settings.get(TASK_SETTINGS_KEYS["enable_task_tags"], True),
        max_tags_per_task=settings.get(TASK_SETTINGS_KEYS["max_tags_per_task"], 10),
        enable_task_checklist=settings.get(TASK_SETTINGS_KEYS["enable_task_checklist"], True),
        max_checklist_items=settings.get(TASK_SETTINGS_KEYS["max_checklist_items"], 20),
        enable_task_assignments=settings.get(TASK_SETTINGS_KEYS["enable_task_assignments"], True),
        max_assignees_per_task=settings.get(TASK_SETTINGS_KEYS["max_assignees_per_task"], 5),
        enable_task_history=settings.get(TASK_SETTINGS_KEYS["enable_task_history"], True),
        history_retention_days=settings.get(TASK_SETTINGS_KEYS["history_retention_days"], 90),
    )




