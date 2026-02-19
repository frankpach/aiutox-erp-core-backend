"""Activity models for timeline and activity tracking."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class ActivityType(str, Enum):
    """Types of activities."""

    COMMENT = "comment"
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TASK = "task"
    STATUS_CHANGE = "status_change"
    NOTE = "note"
    FILE_UPLOAD = "file_upload"
    CUSTOM = "custom"


class Activity(Base):
    """Activity model for timeline tracking."""

    __tablename__ = "activities"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Polymorphic relationship
    entity_type = Column(String(50), nullable=False, index=True)  # e.g., 'product', 'order', 'contact'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Activity information
    activity_type = Column(String(50), nullable=False, index=True)  # comment, call, email, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # User who created the activity
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    activity_metadata = Column("metadata", JSONB, nullable=True)  # Additional metadata as JSON

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_activities_entity", "entity_type", "entity_id"),
        Index("idx_activities_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("idx_activities_created", "tenant_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, type={self.activity_type}, entity={self.entity_type}:{self.entity_id})>"

