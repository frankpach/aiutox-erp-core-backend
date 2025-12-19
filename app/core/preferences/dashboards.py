"""Dashboards management for user preferences."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.preference_repository import PreferenceRepository

logger = logging.getLogger(__name__)


class DashboardsService:
    """Service for managing dashboards."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = PreferenceRepository(db)

    def create_dashboard(
        self,
        user_id: UUID,
        tenant_id: UUID,
        name: str,
        widgets: list[dict[str, Any]],
        is_default: bool = False,
    ) -> dict[str, Any]:
        """Create a dashboard.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            name: Dashboard name
            widgets: List of widget configurations
            is_default: Whether this is the default dashboard

        Returns:
            Dictionary with dashboard data
        """
        # If setting as default, unset other defaults
        if is_default:
            dashboards = self.repository.get_dashboards(user_id, tenant_id)
            for dashboard in dashboards:
                if dashboard.is_default:
                    dashboard.is_default = False
            self.db.commit()

        dashboard = self.repository.create_dashboard(
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "name": name,
                "widgets": widgets,
                "is_default": is_default,
            }
        )
        logger.info(f"Created dashboard '{name}' for user {user_id}")
        return {
            "id": dashboard.id,
            "user_id": dashboard.user_id,
            "tenant_id": dashboard.tenant_id,
            "name": dashboard.name,
            "widgets": dashboard.widgets,
            "is_default": dashboard.is_default,
            "created_at": dashboard.created_at.isoformat(),
            "updated_at": dashboard.updated_at.isoformat(),
        }

    def get_dashboards(self, user_id: UUID, tenant_id: UUID) -> list[dict[str, Any]]:
        """Get dashboards for a user.

        Args:
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            List of dashboard dictionaries
        """
        dashboards = self.repository.get_dashboards(user_id, tenant_id)
        return [
            {
                "id": dashboard.id,
                "user_id": dashboard.user_id,
                "tenant_id": dashboard.tenant_id,
                "name": dashboard.name,
                "widgets": dashboard.widgets,
                "is_default": dashboard.is_default,
                "created_at": dashboard.created_at.isoformat(),
                "updated_at": dashboard.updated_at.isoformat(),
            }
            for dashboard in dashboards
        ]

    def update_dashboard(
        self,
        dashboard_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        name: str | None = None,
        widgets: list[dict[str, Any]] | None = None,
        is_default: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update a dashboard.

        Args:
            dashboard_id: Dashboard ID
            user_id: User ID
            tenant_id: Tenant ID
            name: New name (optional)
            widgets: New widgets (optional)
            is_default: New is_default status (optional)

        Returns:
            Updated dashboard dictionary or None if not found
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if widgets is not None:
            update_data["widgets"] = widgets
        if is_default is not None:
            update_data["is_default"] = is_default
            # If setting as default, unset other defaults
            if is_default:
                dashboards = self.repository.get_dashboards(user_id, tenant_id)
                for dashboard in dashboards:
                    if dashboard.id != dashboard_id and dashboard.is_default:
                        dashboard.is_default = False
                self.db.commit()

        dashboard = self.repository.update_dashboard(
            dashboard_id, user_id, tenant_id, update_data
        )
        if not dashboard:
            return None

        return {
            "id": dashboard.id,
            "user_id": dashboard.user_id,
            "tenant_id": dashboard.tenant_id,
            "name": dashboard.name,
            "widgets": dashboard.widgets,
            "is_default": dashboard.is_default,
            "created_at": dashboard.created_at.isoformat(),
            "updated_at": dashboard.updated_at.isoformat(),
        }

    def delete_dashboard(
        self, dashboard_id: UUID, user_id: UUID, tenant_id: UUID
    ) -> bool:
        """Delete a dashboard.

        Args:
            dashboard_id: Dashboard ID
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        return self.repository.delete_dashboard(dashboard_id, user_id, tenant_id)










