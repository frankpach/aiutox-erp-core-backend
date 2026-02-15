"""Notifications module for notification system."""

from fastapi import APIRouter

from app.core.module_interface import ModuleInterface, ModuleNavigationItem
from app.core.notifications.service import NotificationService


class NotificationsCoreModule(ModuleInterface):
    """Core notifications module metadata for dynamic navigation."""

    @property
    def module_id(self) -> str:
        return "notifications"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_router(self) -> APIRouter | None:
        from app.api.v1.notifications import router

        return router

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="notifications.config",
                label="Notificaciones",
                path="/config/notifications",
                permission="notifications.view",
                icon="settings",
                category="Configuración",
                order=30,
            )
        ]


def create_module(_db: object | None = None) -> NotificationsCoreModule:
    return NotificationsCoreModule()

__all__ = [
    "NotificationService",
    "NotificationsCoreModule",
    "create_module",
]










