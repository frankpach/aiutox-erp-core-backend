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
        """Get saved filters with optional filters."""
        query = self.db.query(SavedFilter).filter(SavedFilter.tenant_id == tenant_id)

        if module:
            query = query.filter(SavedFilter.module == module)
        if user_id:
            query = query.filter(SavedFilter.created_by == user_id)
        if is_shared is not None:
            query = query.filter(SavedFilter.is_shared == is_shared)

        return query.order_by(SavedFilter.created_at.desc()).offset(skip).limit(limit).all()

    def update_saved_filter(self, filter_obj: SavedFilter, filter_data: dict) -> SavedFilter:
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

    def get_custom_view_by_id(self, view_id: UUID, tenant_id: UUID) -> CustomView | None:
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

        return query.order_by(CustomView.created_at.desc()).offset(skip).limit(limit).all()

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








