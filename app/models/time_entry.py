"""Time entry model for task time tracking."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class TimeEntry(Base):
    """Time entry model for tracking work sessions on tasks."""

    __tablename__ = "time_entries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Time tracking
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)  # Calculated on stop

    # Metadata
    notes = Column(Text, nullable=True)
    entry_type = Column(
        String(20), nullable=False, default="manual"
    )  # "manual" | "timer"

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

    # Relationships
    task = relationship("Task", backref="time_entries")

    __table_args__ = (
        Index("idx_time_entries_task", "tenant_id", "task_id"),
        Index("idx_time_entries_user", "tenant_id", "user_id"),
        Index("idx_time_entries_active", "tenant_id", "user_id", "end_time"),
    )

    def __repr__(self) -> str:
        return f"<TimeEntry(id={self.id}, task_id={self.task_id}, user_id={self.user_id})>"
