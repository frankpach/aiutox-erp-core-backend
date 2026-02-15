"""Integrations module for external integrations and webhooks."""

from fastapi import APIRouter

from app.core.integrations.service import IntegrationService
from app.core.integrations.webhooks import WebhookHandler
from app.core.module_interface import ModuleInterface, ModuleNavigationItem


class IntegrationsCoreModule(ModuleInterface):
    """Core integrations module metadata for dynamic navigation."""

    @property
    def module_id(self) -> str:
        return "integrations"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_router(self) -> APIRouter | None:
        from app.api.v1.integrations import router

        return router

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="integrations.config",
                label="Integraciones",
                path="/config/integrations",
                permission="integrations.view",
                icon="plug",
                category="Configuración",
                order=50,
            ),
            ModuleNavigationItem(
                id="integrations.webhooks",
                label="Webhooks",
                path="/config/webhooks",
                permission="integrations.view",
                icon="plug",
                category="Configuración",
                order=60,
            ),
        ]


def create_module(_db: object | None = None) -> IntegrationsCoreModule:
    return IntegrationsCoreModule()

__all__ = [
    "IntegrationService",
    "WebhookHandler",
    "IntegrationsCoreModule",
    "create_module",
]








