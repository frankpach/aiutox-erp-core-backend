"""Views management for user preferences."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.preference_repository import PreferenceRepository

logger = logging.getLogger(__name__)


class ViewsService:
    """Service for managing saved views."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = PreferenceRepository(db)

    def save_view(
        self,
        user_id: UUID,
        tenant_id: UUID,
        module: str,
        name: str,
        config: dict[str, Any],
        is_default: bool = False,
    ) -> dict[str, Any]:
        """Save a view.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            module: Module name (e.g., 'products')
            name: View name
            config: View configuration
            is_default: Whether this is the default view

        Returns:
            Dictionary with saved view data
        """
        # If setting as default, unset other defaults for this module
        if is_default:
            views = self.repository.get_saved_views(user_id, tenant_id, module)
            for view in views:
                if view.is_default:
                    view.is_default = False
            self.db.commit()

        view = self.repository.create_saved_view(
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "module": module,
                "name": name,
                "config": config,
                "is_default": is_default,
            }
        )
        logger.info(f"Saved view '{name}' for user {user_id} in module {module}")
        return {
            "id": view.id,
            "user_id": view.user_id,
            "tenant_id": view.tenant_id,
            "module": view.module,
            "name": view.name,
            "config": view.config,
            "is_default": view.is_default,
            "created_at": view.created_at.isoformat(),
            "updated_at": view.updated_at.isoformat(),
        }

    def get_views(
        self, user_id: UUID, tenant_id: UUID, module: str | None = None
    ) -> list[dict[str, Any]]:
        """Get saved views for a user.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            module: Optional module filter

        Returns:
            List of view dictionaries
        """
        views = self.repository.get_saved_views(user_id, tenant_id, module)
        return [
            {
                "id": view.id,
                "user_id": view.user_id,
                "tenant_id": view.tenant_id,
                "module": view.module,
                "name": view.name,
                "config": view.config,
                "is_default": view.is_default,
                "created_at": view.created_at.isoformat(),
                "updated_at": view.updated_at.isoformat(),
            }
            for view in views
        ]

    def get_default_view(
        self, user_id: UUID, tenant_id: UUID, module: str
    ) -> dict[str, Any] | None:
        """Get the default view for a module.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            module: Module name

        Returns:
            Default view dictionary or None
        """
        views = self.repository.get_saved_views(user_id, tenant_id, module)
        for view in views:
            if view.is_default:
                return {
                    "id": view.id,
                    "user_id": view.user_id,
                    "tenant_id": view.tenant_id,
                    "module": view.module,
                    "name": view.name,
                    "config": view.config,
                    "is_default": view.is_default,
                }
        return None
