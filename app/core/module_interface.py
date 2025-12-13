"""Module interface for all modules in the system."""

from abc import ABC, abstractmethod
from typing import Optional

from fastapi import APIRouter


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

    def get_router(self) -> Optional[APIRouter]:
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



