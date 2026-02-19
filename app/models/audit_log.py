"""AuditLog model for security and audit event tracking."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class AuditLog(Base):
    """AuditLog model for tracking security and audit events."""

    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who performed the action (null for system actions)",
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenancy isolation",
    )
    action = Column(String(100), nullable=False, index=True, comment="Action type (e.g., 'grant_permission', 'create_user')")
    resource_type = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Type of resource affected (e.g., 'user', 'permission', 'role')",
    )
    resource_id = Column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="ID of the resource affected",
    )
    details = Column(JSONB, nullable=True, comment="Additional details as JSON")
    ip_address = Column(String(45), nullable=True, comment="Client IP address (supports IPv6)")
    user_agent = Column(String(500), nullable=True, comment="Client user agent string")
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("idx_audit_logs_action_created", "action", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, "
            f"action={self.action}, resource_type={self.resource_type}, "
            f"created_at={self.created_at})>"
        )

