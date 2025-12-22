"""Integration model for third-party service integrations."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class IntegrationType(str, Enum):
    """Integration type enumeration."""

    STRIPE = "stripe"
    TWILIO = "twilio"
    GOOGLE_CALENDAR = "google_calendar"
    SLACK = "slack"
    ZAPIER = "zapier"
    WEBHOOK = "webhook"
    CUSTOM = "custom"


class IntegrationStatus(str, Enum):
    """Integration status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class WebhookStatus(str, Enum):
    """Webhook delivery status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Integration(Base):
    """Integration model for third-party service integrations."""

    __tablename__ = "integrations"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # IntegrationType
    status = Column(String(20), nullable=False, default=IntegrationStatus.INACTIVE.value)  # IntegrationStatus
    config = Column(JSON, nullable=False, default=dict)  # Credentials and configuration
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, name={self.name}, type={self.type}, status={self.status})>"


class Webhook(Base):
    """Webhook model for webhook configurations."""

    __tablename__ = "webhooks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    integration_id = Column(PostgresUUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    method = Column(String(10), nullable=False, default="POST")
    headers = Column(JSON, nullable=True)
    secret = Column(String(255), nullable=True)
    max_retries = Column(Integer, nullable=False, default=3)
    retry_delay = Column(Integer, nullable=False, default=60)
    extra_data = Column("metadata", JSON, nullable=True)  # Maps Python attribute 'extra_data' to DB column 'metadata'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    integration = relationship("Integration", backref="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, name={self.name}, event_type={self.event_type}, enabled={self.enabled})>"


class WebhookDelivery(Base):
    """Webhook delivery model for tracking webhook deliveries."""

    __tablename__ = "webhook_deliveries"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    webhook_id = Column(PostgresUUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=WebhookStatus.PENDING.value, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<WebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, status={self.status})>"
