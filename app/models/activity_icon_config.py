"""
Activity Icon Configuration Model
Stores custom icon configurations for different activity types and statuses
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.db.base_class import Base


class ActivityIconConfig(Base):
    """
    Model for storing activity icon configurations per tenant.
    Allows customization of icons for different activity types and their statuses.
    """

    __tablename__ = "activity_icon_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    activity_type = Column(
        String(50), nullable=False
    )  # "task", "meeting", "event", "project", "workflow"
    status = Column(String(50), nullable=False)  # "todo", "in_progress", "done", etc.
    icon = Column(String(10), nullable=False)  # Emoji or icon character
    class_name = Column(String(100), nullable=True)  # CSS classes for styling
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index(
            "idx_tenant_activity_status",
            "tenant_id",
            "activity_type",
            "status",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<ActivityIconConfig(id={self.id}, tenant_id={self.tenant_id}, activity_type={self.activity_type}, status={self.status}, icon={self.icon})>"
