"""Import/Export module for data import and export management."""

from fastapi import APIRouter

from app.core.import_export.service import (
    DataExporter,
    DataImporter,
    ImportExportService,
)
from app.core.module_interface import ModuleInterface, ModuleNavigationItem


class ImportExportCoreModule(ModuleInterface):
    """Core import/export module metadata for dynamic navigation."""

    @property
    def module_id(self) -> str:
        return "import_export"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_router(self) -> APIRouter | None:
        from app.api.v1.import_export import router

        return router

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="import_export.config",
                label="Importación y exportación",
                path="/config/import-export",
                permission="import_export.view",
                icon="settings",
                category="Configuración",
                order=70,
            )
        ]


def create_module(_db: object | None = None) -> ImportExportCoreModule:
    return ImportExportCoreModule()

__all__ = [
    "DataExporter",
    "DataImporter",
    "ImportExportService",
    "ImportExportCoreModule",
    "create_module",
]








