"""Tasks module for task management."""

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import (
    ModuleInterface,
    ModuleNavigationItem,
    ModuleNavigationSettingRequirement,
)
from app.models.task import (
    Task,
    TaskChecklistItem,
    Workflow,
    WorkflowExecution,
    WorkflowStep,
)
from app.modules.tasks.api import router
from app.modules.tasks.permissions import TASKS_MANAGE, TASKS_VIEW


class TasksModule(ModuleInterface):
    """Tasks module for task management."""

    def __init__(self, db: Session | None = None):
        self._db = db
        self._config_service = ConfigService(db) if db else None

    @property
    def module_id(self) -> str:
        return "tasks"

    @property
    def module_type(self) -> str:
        return "business"

    @property
    def enabled(self) -> bool:
        if self._db and self._config_service:
            try:
                return True
            except Exception:
                pass
        return True

    def get_router(self) -> APIRouter | None:
        return router

    def get_models(self) -> list:
        return [Task, TaskChecklistItem, Workflow, WorkflowStep, WorkflowExecution]

    def get_dependencies(self) -> list[str]:
        return ["auth", "users", "notifications"]

    @property
    def module_name(self) -> str:
        return "Tareas"

    @property
    def description(self) -> str:
        return "Módulo empresarial: tareas, checklist y soporte de workflows."

    def get_navigation_items(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="tasks.main",
                label="Tareas",
                path="/tasks",
                permission=TASKS_VIEW,
                icon="grid",
                order=0,
            ),
            ModuleNavigationItem(
                id="tasks.status_customizer",
                label="Estados y workflows",
                path="/tasks/status-customizer",
                permission=TASKS_VIEW,
                icon="grid",
                order=20,
            ),
        ]

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="tasks.settings",
                label="Configuración de tareas",
                path="/tasks/settings",
                permission=TASKS_MANAGE,
                icon="settings",
                category="Configuración",
                order=0,
            ),
            ModuleNavigationItem(
                id="tasks.calendar_toggle",
                label="Calendario de tareas",
                path="/calendar",
                permission=TASKS_VIEW,
                icon="calendar",
                category="Configuración",
                order=10,
                requires_module_setting=ModuleNavigationSettingRequirement(
                    module="tasks",
                    key="calendar.enabled",
                    value=True,
                ),
            ),
        ]


def create_module(db: Session | None = None) -> TasksModule:
    return TasksModule(db)
