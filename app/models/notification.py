"""Notification models for notification system."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class NotificationStatus(str, Enum):
    """Status of notification in queue."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationTemplate(Base):
    """Notification template model."""

    __tablename__ = "notification_templates"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)  # e.g., 'product.created'
    channel = Column(String(50), nullable=False)  # 'email', 'sms', 'webhook', 'in-app'
    subject = Column(String(500), nullable=True)  # For email
    body = Column(Text, nullable=False)  # Template body with {{variables}}
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_notification_templates_tenant_event", "tenant_id", "event_type"),
        Index("idx_notification_templates_event_channel", "event_type", "channel"),
    )


class NotificationQueue(Base):
    """Notification queue model."""

    __tablename__ = "notification_queue"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    recipient_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(50), nullable=False, index=True)  # 'email', 'sms', 'webhook', 'in-app'
    template_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("notification_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data = Column(JSONB, nullable=True)  # Event data for template rendering
    status = Column(String(20), nullable=False, default=NotificationStatus.PENDING, index=True)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("idx_notification_queue_status", "status"),
        Index("idx_notification_queue_created", "created_at"),
    )










