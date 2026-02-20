"""View repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.view import CustomView, SavedFilter, ViewShare


class ViewRepository:
    """Repository for view data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Saved Filter methods
    def create_saved_filter(self, filter_data: dict) -> SavedFilter:
        """Create a new saved filter."""
        filter_obj = SavedFilter(**filter_data)
        self.db.add(filter_obj)
        self.db.commit()
        self.db.refresh(filter_obj)
        return filter_obj

    def get_saved_filter_by_id(
        self, filter_id: UUID, tenant_id: UUID
    ) -> SavedFilter | None:
        """Get saved filter by ID and tenant."""
        return (
            self.db.query(SavedFilter)
            .filter(SavedFilter.id == filter_id, SavedFilter.tenant_id == tenant_id)
            .first()
        )

    def get_saved_filters(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SavedFilter]:
        """Get saved filters with optional filters.

        Returns filters where:
        - If user_id is provided: filters created by user OR shared filters
        - If is_shared is True: only shared filters
        - If is_shared is False: only non-shared filters created by user
        - If is_shared is None and user_id is provided: user's filters OR shared filters
        """
        from sqlalchemy import or_

        query = self.db.query(SavedFilter).filter(SavedFilter.tenant_id == tenant_id)

        if module:
            query = query.filter(SavedFilter.module == module)

        # Handle user_id and is_shared logic
        if user_id is not None:
            if is_shared is True:
                # Only shared filters
                query = query.filter(SavedFilter.is_shared)
            elif is_shared is False:
                # Only user's non-shared filters
                query = query.filter(
                    SavedFilter.created_by == user_id, not SavedFilter.is_shared
                )
            else:
                # User's filters OR shared filters
                query = query.filter(
                    or_(SavedFilter.created_by == user_id, SavedFilter.is_shared)
                )
        elif is_shared is not None:
            # Filter by shared status only (no user filter)
            query = query.filter(SavedFilter.is_shared == is_shared)

        return (
            query.order_by(SavedFilter.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_saved_filters(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
    ) -> int:
        """Count saved filters with optional filters."""
        from sqlalchemy import func, or_

        query = self.db.query(func.count(SavedFilter.id)).filter(
            SavedFilter.tenant_id == tenant_id
        )

        if module:
            query = query.filter(SavedFilter.module == module)

        # Handle user_id and is_shared logic (same as get_saved_filters)
        if user_id is not None:
            if is_shared is True:
                query = query.filter(SavedFilter.is_shared)
            elif is_shared is False:
                query = query.filter(
                    SavedFilter.created_by == user_id, not SavedFilter.is_shared
                )
            else:
                query = query.filter(
                    or_(SavedFilter.created_by == user_id, SavedFilter.is_shared)
                )
        elif is_shared is not None:
            query = query.filter(SavedFilter.is_shared == is_shared)

        return query.scalar() or 0

    def update_saved_filter(
        self, filter_obj: SavedFilter, filter_data: dict
    ) -> SavedFilter:
        """Update saved filter."""
        for key, value in filter_data.items():
            setattr(filter_obj, key, value)
        self.db.commit()
        self.db.refresh(filter_obj)
        return filter_obj

    def delete_saved_filter(self, filter_obj: SavedFilter) -> None:
        """Delete saved filter."""
        self.db.delete(filter_obj)
        self.db.commit()

    # Custom View methods
    def create_custom_view(self, view_data: dict) -> CustomView:
        """Create a new custom view."""
        view = CustomView(**view_data)
        self.db.add(view)
        self.db.commit()
        self.db.refresh(view)
        return view

    def get_custom_view_by_id(
        self, view_id: UUID, tenant_id: UUID
    ) -> CustomView | None:
        """Get custom view by ID and tenant."""
        return (
            self.db.query(CustomView)
            .filter(CustomView.id == view_id, CustomView.tenant_id == tenant_id)
            .first()
        )

    def get_custom_views(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CustomView]:
        """Get custom views with optional filters."""
        query = self.db.query(CustomView).filter(CustomView.tenant_id == tenant_id)

        if module:
            query = query.filter(CustomView.module == module)
        if user_id:
            query = query.filter(CustomView.created_by == user_id)
        if is_shared is not None:
            query = query.filter(CustomView.is_shared == is_shared)

        return (
            query.order_by(CustomView.created_at.desc()).offset(skip).limit(limit).all()
        )

    def count_custom_views(
        self,
        tenant_id: UUID,
        module: str | None = None,
        user_id: UUID | None = None,
        is_shared: bool | None = None,
    ) -> int:
        """Count custom views with optional filters."""
        query = self.db.query(CustomView).filter(CustomView.tenant_id == tenant_id)

        if module:
            query = query.filter(CustomView.module == module)
        if user_id:
            query = query.filter(CustomView.created_by == user_id)
        if is_shared is not None:
            query = query.filter(CustomView.is_shared == is_shared)

        return query.count()

    def update_custom_view(self, view: CustomView, view_data: dict) -> CustomView:
        """Update custom view."""
        for key, value in view_data.items():
            setattr(view, key, value)
        self.db.commit()
        self.db.refresh(view)
        return view

    def delete_custom_view(self, view: CustomView) -> None:
        """Delete custom view."""
        self.db.delete(view)
        self.db.commit()

    # View Share methods
    def create_view_share(self, share_data: dict) -> ViewShare:
        """Create a new view share."""
        share = ViewShare(**share_data)
        self.db.add(share)
        self.db.commit()
        self.db.refresh(share)
        return share

    def get_view_shares(
        self,
        tenant_id: UUID,
        filter_id: UUID | None = None,
        view_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> list[ViewShare]:
        """Get view shares with optional filters."""
        query = self.db.query(ViewShare).filter(ViewShare.tenant_id == tenant_id)

        if filter_id:
            query = query.filter(ViewShare.filter_id == filter_id)
        if view_id:
            query = query.filter(ViewShare.view_id == view_id)
        if user_id:
            query = query.filter(ViewShare.shared_with_user_id == user_id)

        return query.all()

    def delete_view_share(self, share: ViewShare) -> None:
        """Delete view share."""
        self.db.delete(share)
        self.db.commit()
