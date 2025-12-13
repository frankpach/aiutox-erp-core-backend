"""Preference repository for data access operations."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.preference import Dashboard, OrgPreference, RolePreference, SavedView, UserPreference


class PreferenceRepository:
    """Repository for preference data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # UserPreference operations
    def get_user_preference(
        self, user_id: UUID, tenant_id: UUID, preference_type: str, key: str
    ) -> UserPreference | None:
        """Get a user preference."""
        return (
            self.db.query(UserPreference)
            .filter(
                UserPreference.user_id == user_id,
                UserPreference.tenant_id == tenant_id,
                UserPreference.preference_type == preference_type,
                UserPreference.key == key,
            )
            .first()
        )

    def get_all_user_preferences(
        self, user_id: UUID, tenant_id: UUID, preference_type: str | None = None
    ) -> list[UserPreference]:
        """Get all user preferences, optionally filtered by type."""
        query = self.db.query(UserPreference).filter(
            UserPreference.user_id == user_id, UserPreference.tenant_id == tenant_id
        )
        if preference_type:
            query = query.filter(UserPreference.preference_type == preference_type)
        return query.all()

    def create_or_update_user_preference(
        self, user_id: UUID, tenant_id: UUID, preference_type: str, key: str, value: Any
    ) -> UserPreference:
        """Create or update a user preference."""
        existing = self.get_user_preference(user_id, tenant_id, preference_type, key)
        if existing:
            existing.value = value
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            preference = UserPreference(
                user_id=user_id,
                tenant_id=tenant_id,
                preference_type=preference_type,
                key=key,
                value=value,
            )
            self.db.add(preference)
            self.db.commit()
            self.db.refresh(preference)
            return preference

    def delete_user_preference(
        self, user_id: UUID, tenant_id: UUID, preference_type: str, key: str
    ) -> bool:
        """Delete a user preference."""
        preference = self.get_user_preference(user_id, tenant_id, preference_type, key)
        if not preference:
            return False
        self.db.delete(preference)
        self.db.commit()
        return True

    # OrgPreference operations
    def get_org_preference(
        self, tenant_id: UUID, preference_type: str, key: str
    ) -> OrgPreference | None:
        """Get an organization preference."""
        return (
            self.db.query(OrgPreference)
            .filter(
                OrgPreference.tenant_id == tenant_id,
                OrgPreference.preference_type == preference_type,
                OrgPreference.key == key,
            )
            .first()
        )

    def get_all_org_preferences(
        self, tenant_id: UUID, preference_type: str | None = None
    ) -> list[OrgPreference]:
        """Get all organization preferences, optionally filtered by type."""
        query = self.db.query(OrgPreference).filter(OrgPreference.tenant_id == tenant_id)
        if preference_type:
            query = query.filter(OrgPreference.preference_type == preference_type)
        return query.all()

    def create_or_update_org_preference(
        self, tenant_id: UUID, preference_type: str, key: str, value: Any
    ) -> OrgPreference:
        """Create or update an organization preference."""
        existing = self.get_org_preference(tenant_id, preference_type, key)
        if existing:
            existing.value = value
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            preference = OrgPreference(
                tenant_id=tenant_id, preference_type=preference_type, key=key, value=value
            )
            self.db.add(preference)
            self.db.commit()
            self.db.refresh(preference)
            return preference

    # RolePreference operations
    def get_role_preference(
        self, role_id: UUID, tenant_id: UUID, preference_type: str, key: str
    ) -> RolePreference | None:
        """Get a role preference."""
        return (
            self.db.query(RolePreference)
            .filter(
                RolePreference.role_id == role_id,
                RolePreference.tenant_id == tenant_id,
                RolePreference.preference_type == preference_type,
                RolePreference.key == key,
            )
            .first()
        )

    def get_all_role_preferences(
        self, role_id: UUID, tenant_id: UUID, preference_type: str | None = None
    ) -> list[RolePreference]:
        """Get all role preferences, optionally filtered by type."""
        query = self.db.query(RolePreference).filter(
            RolePreference.role_id == role_id, RolePreference.tenant_id == tenant_id
        )
        if preference_type:
            query = query.filter(RolePreference.preference_type == preference_type)
        return query.all()

    def create_or_update_role_preference(
        self, role_id: UUID, tenant_id: UUID, preference_type: str, key: str, value: Any
    ) -> RolePreference:
        """Create or update a role preference."""
        existing = self.get_role_preference(role_id, tenant_id, preference_type, key)
        if existing:
            existing.value = value
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            preference = RolePreference(
                role_id=role_id,
                tenant_id=tenant_id,
                preference_type=preference_type,
                key=key,
                value=value,
            )
            self.db.add(preference)
            self.db.commit()
            self.db.refresh(preference)
            return preference

    # SavedView operations
    def create_saved_view(self, view_data: dict) -> SavedView:
        """Create a saved view."""
        view = SavedView(**view_data)
        self.db.add(view)
        self.db.commit()
        self.db.refresh(view)
        return view

    def get_saved_views(
        self, user_id: UUID, tenant_id: UUID, module: str | None = None
    ) -> list[SavedView]:
        """Get saved views for a user."""
        query = self.db.query(SavedView).filter(
            SavedView.user_id == user_id, SavedView.tenant_id == tenant_id
        )
        if module:
            query = query.filter(SavedView.module == module)
        return query.all()

    def get_saved_view_by_id(
        self, view_id: UUID, user_id: UUID, tenant_id: UUID
    ) -> SavedView | None:
        """Get a saved view by ID."""
        return (
            self.db.query(SavedView)
            .filter(
                SavedView.id == view_id,
                SavedView.user_id == user_id,
                SavedView.tenant_id == tenant_id,
            )
            .first()
        )

    def update_saved_view(
        self, view_id: UUID, user_id: UUID, tenant_id: UUID, view_data: dict
    ) -> SavedView | None:
        """Update a saved view."""
        view = self.get_saved_view_by_id(view_id, user_id, tenant_id)
        if not view:
            return None
        for key, value in view_data.items():
            setattr(view, key, value)
        self.db.commit()
        self.db.refresh(view)
        return view

    def delete_saved_view(self, view_id: UUID, user_id: UUID, tenant_id: UUID) -> bool:
        """Delete a saved view."""
        view = self.get_saved_view_by_id(view_id, user_id, tenant_id)
        if not view:
            return False
        self.db.delete(view)
        self.db.commit()
        return True

    # Dashboard operations
    def create_dashboard(self, dashboard_data: dict) -> Dashboard:
        """Create a dashboard."""
        dashboard = Dashboard(**dashboard_data)
        self.db.add(dashboard)
        self.db.commit()
        self.db.refresh(dashboard)
        return dashboard

    def get_dashboards(self, user_id: UUID, tenant_id: UUID) -> list[Dashboard]:
        """Get dashboards for a user."""
        return (
            self.db.query(Dashboard)
            .filter(Dashboard.user_id == user_id, Dashboard.tenant_id == tenant_id)
            .all()
        )

    def get_dashboard_by_id(
        self, dashboard_id: UUID, user_id: UUID, tenant_id: UUID
    ) -> Dashboard | None:
        """Get a dashboard by ID."""
        return (
            self.db.query(Dashboard)
            .filter(
                Dashboard.id == dashboard_id,
                Dashboard.user_id == user_id,
                Dashboard.tenant_id == tenant_id,
            )
            .first()
        )

    def update_dashboard(
        self, dashboard_id: UUID, user_id: UUID, tenant_id: UUID, dashboard_data: dict
    ) -> Dashboard | None:
        """Update a dashboard."""
        dashboard = self.get_dashboard_by_id(dashboard_id, user_id, tenant_id)
        if not dashboard:
            return None
        for key, value in dashboard_data.items():
            setattr(dashboard, key, value)
        self.db.commit()
        self.db.refresh(dashboard)
        return dashboard

    def delete_dashboard(self, dashboard_id: UUID, user_id: UUID, tenant_id: UUID) -> bool:
        """Delete a dashboard."""
        dashboard = self.get_dashboard_by_id(dashboard_id, user_id, tenant_id)
        if not dashboard:
            return False
        self.db.delete(dashboard)
        self.db.commit()
        return True



