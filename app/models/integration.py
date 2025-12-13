"""Integration models for external integrations and webhooks."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID

from app.core.db.session import Base


class IntegrationType(str, Enum):
    """Integration type enumeration."""

    WEBHOOK = "webhook"
    API = "api"
    OAUTH = "oauth"
    CUSTOM = "custom"


class IntegrationStatus(str, Enum):
    """Integration status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class WebhookStatus(str, Enum):
    """Webhook delivery status enumeration."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class Integration(Base):
    """Integration model for external integrations."""

    __tablename__ = "integrations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Integration information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    integration_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=IntegrationStatus.ACTIVE, index=True)

    # Configuration
    config = Column(JSONB, nullable=False)  # Integration-specific configuration
    credentials = Column(Text, nullable=True)  # Encrypted credentials (JSON string)

    # Metadata
    integration_metadata = Column("metadata", JSONB, nullable=True)  # Additional metadata

    # Timestamps
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
    last_sync_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_integrations_tenant_status", "tenant_id", "status"),
        Index("idx_integrations_tenant_type", "tenant_id", "integration_type"),
    )

    def __repr__(self) -> str:
        return f"<Integration(id={self.id}, name={self.name}, type={self.integration_type})>"


class Webhook(Base):
    """Webhook model for configurable webhooks."""

    __tablename__ = "webhooks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    integration_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Webhook information
    name = Column(String(255), nullable=False)
    url = Column(String(1000), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)  # e.g., 'product.created', 'order.completed'
    enabled = Column(Boolean, default=True, nullable=False, index=True)

    # Configuration
    method = Column(String(10), default="POST", nullable=False)  # HTTP method
    headers = Column(JSONB, nullable=True)  # Custom headers
    secret = Column(String(255), nullable=True)  # Secret for signature validation

    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay = Column(Integer, default=60, nullable=False)  # Seconds

    # Metadata
    webhook_metadata = Column("metadata", JSONB, nullable=True)

    # Timestamps
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
        Index("idx_webhooks_tenant_event", "tenant_id", "event_type"),
        Index("idx_webhooks_tenant_enabled", "tenant_id", "enabled"),
    )

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, name={self.name}, event_type={self.event_type})>"


class WebhookDelivery(Base):
    """Webhook delivery model for tracking webhook deliveries."""

    __tablename__ = "webhook_deliveries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    webhook_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Delivery information
    status = Column(String(20), nullable=False, default=WebhookStatus.PENDING, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)  # Webhook payload

    # Response information
    response_status = Column(Integer, nullable=True)  # HTTP status code
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Retry information
    retry_count = Column(Integer, default=0, nullable=False)
    next_retry_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_webhook_deliveries_webhook_status", "webhook_id", "status"),
        Index("idx_webhook_deliveries_tenant_created", "tenant_id", "created_at"),
        Index("idx_webhook_deliveries_retry", "status", "next_retry_at"),
    )

    def __repr__(self) -> str:
        return f"<WebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, status={self.status})>"


class IntegrationLog(Base):
    """Integration log model for tracking integration activities."""

    __tablename__ = "integration_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    integration_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("integrations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Log information
    action = Column(String(100), nullable=False)  # e.g., 'sync', 'webhook_sent', 'error'
    status = Column(String(20), nullable=False)  # success, error, warning
    message = Column(Text, nullable=True)
    data = Column(JSONB, nullable=True)  # Additional log data

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        Index("idx_integration_logs_integration_created", "integration_id", "created_at"),
        Index("idx_integration_logs_tenant_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<IntegrationLog(id={self.id}, integration_id={self.integration_id}, action={self.action})>"

