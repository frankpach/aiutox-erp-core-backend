"""Files module for file and document management."""

from fastapi import APIRouter

# Import tasks to register them
from app.core.files import tasks  # noqa: F401
from app.core.files.service import FileService
from app.core.files.storage import (
    BaseStorageBackend,
    HybridStorageBackend,
    LocalStorageBackend,
    S3StorageBackend,
)
from app.core.module_interface import ModuleInterface, ModuleNavigationItem


class FilesCoreModule(ModuleInterface):
    """Core files module metadata for dynamic navigation."""

    @property
    def module_id(self) -> str:
        return "files"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_router(self) -> APIRouter | None:
        from app.api.v1.files import router

        return router

    def get_navigation_items(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="files.main",
                label="Archivos",
                path="/files",
                permission="files.view",
                icon="grid",
                order=0,
            )
        ]

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="files.config",
                label="Configuración de archivos",
                path="/config/files",
                permission="files.manage",
                icon="settings",
                category="Configuración",
                order=40,
            )
        ]


def create_module(_db: object | None = None) -> FilesCoreModule:
    return FilesCoreModule()

__all__ = [
    "FileService",
    "BaseStorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "HybridStorageBackend",
    "FilesCoreModule",
    "create_module",
]

