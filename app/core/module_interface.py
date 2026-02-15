"""Module interface for all modules in the system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter


@dataclass(slots=True)
class ModuleNavigationSettingRequirement:
    """Requirement for displaying a navigation item based on module settings."""

    module: str
    key: str
    value: Any | None = None


@dataclass(slots=True)
class ModuleNavigationItem:
    """Navigation item exposed by a module (main or configuration)."""

    id: str
    label: str
    path: str
    permission: str | None = None
    icon: str | None = None
    category: str | None = None
    order: int = 0
    badge: int | None = None
    requires_module_setting: ModuleNavigationSettingRequirement | None = None


class ModuleInterface(ABC):
    """Interface that all modules must implement."""

    @property
    @abstractmethod
    def module_id(self) -> str:
        """Unique module identifier (e.g., 'products', 'auth').

        Returns:
            Module ID in snake_case
        """
        pass

    @property
    @abstractmethod
    def module_type(self) -> str:
        """Module type: 'core' for infrastructure or 'business' for business modules.

        Returns:
            'core' or 'business'
        """
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the module is enabled.

        This should check configuration from ConfigService or default to True.

        Returns:
            True if module is enabled, False otherwise
        """
        pass

    def get_router(self) -> APIRouter | None:
        """Get the FastAPI router for this module.

        Returns:
            APIRouter instance if module has API endpoints, None otherwise
        """
        return None

    def get_models(self) -> list:
        """Get all SQLAlchemy models for this module.

        Returns:
            List of SQLAlchemy model classes
        """
        return []

    def get_dependencies(self) -> list[str]:
        """Get list of module IDs this module depends on.

        Returns:
            List of module IDs (e.g., ['auth', 'users', 'pubsub'])
        """
        return []

    def on_load(self) -> None:
        """Callback called when module is loaded by the registry.

        Use this for initialization tasks like registering data sources,
        notification templates, etc.
        """
        pass

    def get_navigation_items(self) -> list[ModuleNavigationItem]:
        """Main navigation entries exposed by the module."""

        return []

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        """Configuration/navigation entries that should appear under Configuración."""

        return []

    @property
    def module_name(self) -> str:
        """Human-readable module name.

        Returns:
            Module name (defaults to module_id)
        """
        return self.module_id

    @property
    def description(self) -> str:
        """Module description.

        Returns:
            Description string (defaults to empty string)
        """
        return ""










