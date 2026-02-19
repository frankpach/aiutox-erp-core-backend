"""View service for saved filters and custom views management."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pubsub import EventPublisher, get_event_publisher
from app.models.view import CustomView, SavedFilter, ViewShare
from app.repositories.view_repository import ViewRepository

logger = logging.getLogger(__name__)


class ViewService:
    """Service for managing saved filters and custom views."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize view service.

        Args:
            db: Database session
            event_publisher: EventPublisher instance (created if not provided)
        """
        self.db = db
        self.repository = ViewRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()

    # Saved Filter methods
    def create_saved_filter(
        self,
        filter_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> SavedFilter:
        """Create a new saved filter."""
        filter_data["tenant_id"] = tenant_id
        filter_data["created_by"] = user_id

        return self.repository.create_saved_filter(filter_data)

    def get_saved_filter(self, filter_id: UUID, tenant_id: UUID) -> SavedFilter | None:
        """Get saved filter by ID."""
        return self.repository.get_saved_filter_by_id(filter_id, tenant_id)

    def get_saved_filters(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SavedFilter]:
        """Get saved filters."""
        return self.repository.get_saved_filters(
            tenant_id, module, user_id, is_shared, skip, limit
        )

    def count_saved_filters(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
    ) -> int:
        """Count saved filters."""
        return self.repository.count_saved_filters(
            tenant_id, module, user_id, is_shared
        )

    def update_saved_filter(
        self, filter_id: UUID, tenant_id: UUID, filter_data: dict
    ) -> SavedFilter | None:
        """Update saved filter."""
        filter_obj = self.repository.get_saved_filter_by_id(filter_id, tenant_id)
        if not filter_obj:
            return None

        return self.repository.update_saved_filter(filter_obj, filter_data)

    def delete_saved_filter(self, filter_id: UUID, tenant_id: UUID) -> bool:
        """Delete saved filter."""
        filter_obj = self.repository.get_saved_filter_by_id(filter_id, tenant_id)
        if not filter_obj:
            return False

        self.repository.delete_saved_filter(filter_obj)
        return True

    # Custom View methods
    def create_custom_view(
        self,
        view_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> CustomView:
        """Create a new custom view."""
        view_data["tenant_id"] = tenant_id
        view_data["created_by"] = user_id

        return self.repository.create_custom_view(view_data)

    def get_custom_view(self, view_id: UUID, tenant_id: UUID) -> CustomView | None:
        """Get custom view by ID."""
        return self.repository.get_custom_view_by_id(view_id, tenant_id)

    def get_custom_views(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CustomView]:
        """Get custom views."""
        return self.repository.get_custom_views(
            tenant_id, module, user_id, is_shared, skip, limit
        )

    def count_custom_views(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
    ) -> int:
        """Count custom views with optional filters."""
        return self.repository.count_custom_views(
            tenant_id, module, user_id, is_shared
        )

    def update_custom_view(
        self, view_id: UUID, tenant_id: UUID, view_data: dict
    ) -> CustomView | None:
        """Update custom view."""
        view = self.repository.get_custom_view_by_id(view_id, tenant_id)
        if not view:
            return None

        return self.repository.update_custom_view(view, view_data)

    def delete_custom_view(self, view_id: UUID, tenant_id: UUID) -> bool:
        """Delete custom view."""
        view = self.repository.get_custom_view_by_id(view_id, tenant_id)
        if not view:
            return False

        self.repository.delete_custom_view(view)
        return True

    # View Share methods
    def share_filter(
        self,
        filter_id: UUID,
        tenant_id: UUID,
        share_data: dict,
    ) -> ViewShare:
        """Share a filter with other users."""
        share_data["filter_id"] = filter_id
        share_data["tenant_id"] = tenant_id
        return self.repository.create_view_share(share_data)

    def share_view(
        self,
        view_id: UUID,
        tenant_id: UUID,
        share_data: dict,
    ) -> ViewShare:
        """Share a view with other users."""
        share_data["view_id"] = view_id
        share_data["tenant_id"] = tenant_id
        return self.repository.create_view_share(share_data)

    def get_shares(
        self,
        tenant_id: UUID,
        filter_id: UUID | None = None,
        view_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> list[ViewShare]:
        """Get view shares."""
        return self.repository.get_view_shares(tenant_id, filter_id, view_id, user_id)

    def unshare(self, share_id: UUID, tenant_id: UUID) -> bool:
        """Unshare a filter or view."""
        shares = self.repository.get_view_shares(tenant_id)
        share = next((s for s in shares if s.id == share_id), None)
        if not share:
            return False

        self.repository.delete_view_share(share)
        return True








