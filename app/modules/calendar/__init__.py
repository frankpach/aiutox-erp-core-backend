"""Calendar module for calendars and events."""

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.api.v1 import calendar as calendar_module
from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface
from app.models.calendar import Calendar, CalendarEvent, EventAttendee, EventReminder


class CalendarModule(ModuleInterface):
    """Calendar module for calendars and events."""

    def __init__(self, db: Session | None = None):
        self._db = db
        self._config_service = ConfigService(db) if db else None

    @property
    def module_id(self) -> str:
        return "calendar"

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
        return calendar_module.router

    def get_models(self) -> list:
        return [Calendar, CalendarEvent, EventAttendee, EventReminder]

    def get_dependencies(self) -> list[str]:
        return ["auth", "users", "notifications"]

    @property
    def module_name(self) -> str:
        return "Calendario"

    @property
    def description(self) -> str:
        return "Módulo empresarial: calendarios, eventos, asistentes y recordatorios."


def create_module(db: Session | None = None) -> CalendarModule:
    return CalendarModule(db)
