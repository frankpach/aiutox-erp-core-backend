"""Notification repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import NotificationQueue, NotificationTemplate


class NotificationRepository:
    """Repository for notification data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # NotificationTemplate operations
    def create_template(self, template_data: dict) -> NotificationTemplate:
        """Create a new notification template."""
        template = NotificationTemplate(**template_data)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_template(
        self, event_type: str, channel: str, tenant_id: UUID
    ) -> NotificationTemplate | None:
        """Get template by event type, channel, and tenant."""
        return (
            self.db.query(NotificationTemplate)
            .filter(
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.channel == channel,
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.is_active == True,
            )
            .first()
        )

    def get_all_templates(
        self, tenant_id: UUID, event_type: str | None = None
    ) -> list[NotificationTemplate]:
        """Get all templates for a tenant."""
        query = self.db.query(NotificationTemplate).filter(
            NotificationTemplate.tenant_id == tenant_id
        )
        if event_type:
            query = query.filter(NotificationTemplate.event_type == event_type)
        return query.all()

    def update_template(
        self, template_id: UUID, tenant_id: UUID, template_data: dict
    ) -> NotificationTemplate | None:
        """Update a template."""
        template = (
            self.db.query(NotificationTemplate)
            .filter(
                NotificationTemplate.id == template_id,
                NotificationTemplate.tenant_id == tenant_id,
            )
            .first()
        )
        if not template:
            return None
        for key, value in template_data.items():
            setattr(template, key, value)
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template_id: UUID, tenant_id: UUID) -> bool:
        """Delete a template."""
        template = (
            self.db.query(NotificationTemplate)
            .filter(
                NotificationTemplate.id == template_id,
                NotificationTemplate.tenant_id == tenant_id,
            )
            .first()
        )
        if not template:
            return False
        self.db.delete(template)
        self.db.commit()
        return True

    # NotificationQueue operations
    def create_queue_entry(self, queue_data: dict) -> NotificationQueue:
        """Create a new queue entry."""
        queue_entry = NotificationQueue(**queue_data)
        self.db.add(queue_entry)
        self.db.commit()
        self.db.refresh(queue_entry)
        return queue_entry

    def get_queue_entries(
        self, tenant_id: UUID, status: str | None = None, skip: int = 0, limit: int = 100
    ) -> list[NotificationQueue]:
        """Get queue entries."""
        query = self.db.query(NotificationQueue).filter(
            NotificationQueue.tenant_id == tenant_id
        )
        if status:
            query = query.filter(NotificationQueue.status == status)
        return query.order_by(NotificationQueue.created_at.desc()).offset(skip).limit(limit).all()


