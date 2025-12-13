"""Preferences service for user personalization."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.preferences.inheritance import merge_preferences
from app.models.user import User
from app.repositories.preference_repository import PreferenceRepository

logger = logging.getLogger(__name__)


class PreferencesService:
    """Service for managing user preferences."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = PreferenceRepository(db)

    def get_preference(
        self,
        user_id: UUID,
        tenant_id: UUID,
        preference_type: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Get a preference with inheritance (org -> role -> user).

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            preference_type: Preference type (e.g., 'basic', 'notification')
            key: Preference key
            default: Default value if not found

        Returns:
            Preference value with inheritance applied
        """
        # Get preferences from all levels
        org_pref = self.repository.get_org_preference(tenant_id, preference_type, key)
        user_pref = self.repository.get_user_preference(
            user_id, tenant_id, preference_type, key
        )

        # Get role preferences (need to get user's roles first)
        # For now, we'll get all role preferences for the tenant
        # TODO: Filter by user's actual roles when role system is more integrated
        role_prefs_dict = {}
        # This is a simplified version - in production, get user's roles and merge their preferences

        # Build dictionaries for merging
        org_dict = {key: org_pref.value} if org_pref else {}
        role_dict = role_prefs_dict
        user_dict = {key: user_pref.value} if user_pref else {}

        # Merge with inheritance
        merged = merge_preferences(org_dict, role_dict, user_dict)

        return merged.get(key, default)

    def get_all_preferences(
        self, user_id: UUID, tenant_id: UUID, preference_type: str | None = None
    ) -> dict[str, Any]:
        """Get all preferences for a user with inheritance.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            preference_type: Optional preference type filter

        Returns:
            Dictionary of all preferences with inheritance applied
        """
        # Get preferences from all levels
        org_prefs = self.repository.get_all_org_preferences(tenant_id, preference_type)
        user_prefs = self.repository.get_all_user_preferences(
            user_id, tenant_id, preference_type
        )

        # Convert to dictionaries
        org_dict = {pref.key: pref.value for pref in org_prefs}
        user_dict = {pref.key: pref.value for pref in user_prefs}
        role_dict = {}  # TODO: Get actual role preferences

        # Merge with inheritance
        return merge_preferences(org_dict, role_dict, user_dict)

    def set_preference(
        self, user_id: UUID, tenant_id: UUID, preference_type: str, key: str, value: Any
    ) -> dict[str, Any]:
        """Set a user preference.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            preference_type: Preference type
            key: Preference key
            value: Preference value

        Returns:
            Dictionary with preference data
        """
        preference = self.repository.create_or_update_user_preference(
            user_id, tenant_id, preference_type, key, value
        )
        logger.info(
            f"Set preference {preference_type}.{key} for user {user_id} in tenant {tenant_id}"
        )
        return {
            "id": preference.id,
            "user_id": preference.user_id,
            "tenant_id": preference.tenant_id,
            "preference_type": preference.preference_type,
            "key": preference.key,
            "value": preference.value,
        }

    def set_org_preference(
        self, tenant_id: UUID, preference_type: str, key: str, value: Any
    ) -> dict[str, Any]:
        """Set an organization preference.

        Args:
            tenant_id: Tenant ID
            preference_type: Preference type
            key: Preference key
            value: Preference value

        Returns:
            Dictionary with preference data
        """
        preference = self.repository.create_or_update_org_preference(
            tenant_id, preference_type, key, value
        )
        logger.info(f"Set org preference {preference_type}.{key} for tenant {tenant_id}")
        return {
            "id": preference.id,
            "tenant_id": preference.tenant_id,
            "preference_type": preference.preference_type,
            "key": preference.key,
            "value": preference.value,
        }

    def set_role_preference(
        self, role_id: UUID, tenant_id: UUID, preference_type: str, key: str, value: Any
    ) -> dict[str, Any]:
        """Set a role preference.

        Args:
            role_id: Role ID
            tenant_id: Tenant ID
            preference_type: Preference type
            key: Preference key
            value: Preference value

        Returns:
            Dictionary with preference data
        """
        preference = self.repository.create_or_update_role_preference(
            role_id, tenant_id, preference_type, key, value
        )
        logger.info(
            f"Set role preference {preference_type}.{key} for role {role_id} in tenant {tenant_id}"
        )
        return {
            "id": preference.id,
            "role_id": preference.role_id,
            "tenant_id": preference.tenant_id,
            "preference_type": preference.preference_type,
            "key": preference.key,
            "value": preference.value,
        }



