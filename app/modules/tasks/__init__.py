"""Tasks module for task management."""

from typing import Optional

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface
from app.models.task import Task, TaskChecklistItem, Workflow, WorkflowExecution, WorkflowStep
from app.modules.tasks.api import router


class TasksModule(ModuleInterface):
    """Tasks module for task management."""

    def __init__(self, db: Optional[Session] = None):
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

    def get_router(self) -> Optional[APIRouter]:
        return router

    def get_models(self) -> list:
        return [Task, TaskChecklistItem, Workflow, WorkflowStep, WorkflowExecution]

    def get_dependencies(self) -> list[str]:
        return ["auth", "users"]

    @property
    def module_name(self) -> str:
        return "Tareas"

    @property
    def description(self) -> str:
        return "Módulo empresarial: tareas, checklist y soporte de workflows."


def create_module(db: Optional[Session] = None) -> TasksModule:
    return TasksModule(db)
