"""Config module for system configuration management.

This module provides system configuration management (module-specific configs).
For application settings (environment variables), import from app.core.config_file.
"""

from fastapi import APIRouter

from app.core.config.schema import ConfigSchema, config_schema
from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface, ModuleNavigationItem


class ConfigCoreModule(ModuleInterface):
    """Core configuration module metadata for dynamic navigation."""

    @property
    def module_id(self) -> str:
        return "config"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_router(self) -> APIRouter | None:
        from app.api.v1.config import router

        return router

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="config.general",
                label="Configuración general",
                path="/config/general",
                permission="config.view",
                icon="settings",
                category="Configuración",
                order=0,
            ),
            ModuleNavigationItem(
                id="config.theme",
                label="Tema y branding",
                path="/config/theme",
                permission="config.view_theme",
                icon="settings",
                category="Configuración",
                order=10,
            ),
            ModuleNavigationItem(
                id="config.modules",
                label="Gestión de módulos",
                path="/config/modules",
                permission="config.view",
                icon="settings",
                category="Configuración",
                order=20,
            ),
            ModuleNavigationItem(
                id="config.quick_actions",
                label="Acciones rápidas",
                path="/config/quick-actions",
                permission="config.view",
                icon="settings",
                category="Configuración",
                order=25,
            ),
        ]


def create_module(_db: object | None = None) -> ConfigCoreModule:
    return ConfigCoreModule()


__all__ = [
    "ConfigService",
    "ConfigSchema",
    "config_schema",
    "ConfigCoreModule",
    "create_module",
]
