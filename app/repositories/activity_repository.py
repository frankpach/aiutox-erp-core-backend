"""Activity repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity import Activity


class ActivityRepository:
    """Repository for activity data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, activity_data: dict) -> Activity:
        """Create a new activity."""
        activity = Activity(**activity_data)
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def get_by_id(self, activity_id: UUID, tenant_id: UUID) -> Activity | None:
        """Get activity by ID and tenant."""
        return (
            self.db.query(Activity)
            .filter(Activity.id == activity_id, Activity.tenant_id == tenant_id)
            .first()
        )

    def get_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        activity_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Activity]:
        """Get activities by entity."""
        query = self.db.query(Activity).filter(
            Activity.entity_type == entity_type,
            Activity.entity_id == entity_id,
            Activity.tenant_id == tenant_id,
        )
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        return query.order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()

    def count_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        activity_type: str | None = None,
    ) -> int:
        """Count activities by entity."""
        from sqlalchemy import func

        query = self.db.query(func.count(Activity.id)).filter(
            Activity.entity_type == entity_type,
            Activity.entity_id == entity_id,
            Activity.tenant_id == tenant_id,
        )
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        return query.scalar() or 0

    def get_all(
        self,
        tenant_id: UUID,
        activity_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Activity]:
        """Get all activities for a tenant."""
        query = self.db.query(Activity).filter(Activity.tenant_id == tenant_id)
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        return query.order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()

    def count_all(
        self,
        tenant_id: UUID,
        activity_type: str | None = None,
    ) -> int:
        """Count all activities for a tenant."""
        from sqlalchemy import func

        query = self.db.query(func.count(Activity.id)).filter(Activity.tenant_id == tenant_id)
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        return query.scalar() or 0

    def search(
        self,
        tenant_id: UUID,
        query_text: str,
        entity_type: str | None = None,
        activity_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Activity]:
        """Search activities by text."""
        query = (
            self.db.query(Activity)
            .filter(Activity.tenant_id == tenant_id)
            .filter(
                (Activity.title.ilike(f"%{query_text}%"))
                | (Activity.description.ilike(f"%{query_text}%"))
            )
        )
        if entity_type:
            query = query.filter(Activity.entity_type == entity_type)
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        return query.order_by(Activity.created_at.desc()).offset(skip).limit(limit).all()

    def count_search(
        self,
        tenant_id: UUID,
        query_text: str,
        entity_type: str | None = None,
        activity_type: str | None = None,
    ) -> int:
        """Count activities matching search text."""
        from sqlalchemy import func

        query = (
            self.db.query(func.count(Activity.id))
            .filter(Activity.tenant_id == tenant_id)
            .filter(
                (Activity.title.ilike(f"%{query_text}%"))
                | (Activity.description.ilike(f"%{query_text}%"))
            )
        )
        if entity_type:
            query = query.filter(Activity.entity_type == entity_type)
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        return query.scalar() or 0

    def update(
        self, activity_id: UUID, tenant_id: UUID, activity_data: dict
    ) -> Activity | None:
        """Update an activity."""
        activity = self.get_by_id(activity_id, tenant_id)
        if not activity:
            return None
        for key, value in activity_data.items():
            setattr(activity, key, value)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def delete(self, activity_id: UUID, tenant_id: UUID) -> bool:
        """Delete an activity."""
        activity = self.get_by_id(activity_id, tenant_id)
        if not activity:
            return False
        self.db.delete(activity)
        self.db.commit()
        return True

