"""Flow Run models for tracking workflow executions."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class FlowRunStatus(str, Enum):
    """Flow run status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FlowRun(Base):
    """Flow run model for tracking workflow executions."""

    __tablename__ = "flow_runs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flow_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_flows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    status = Column(
        String(50),
        nullable=False,
        default=FlowRunStatus.PENDING.value,
        index=True,
    )
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)
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
    flow = relationship("ApprovalFlow", backref="flow_runs")

    # Indexes
    __table_args__ = (
        Index("idx_flow_runs_tenant_entity", "tenant_id", "entity_type", "entity_id"),
        Index("idx_flow_runs_status_tenant", "status", "tenant_id"),
        Index("idx_flow_runs_flow_tenant", "flow_id", "tenant_id"),
    )

    def __repr__(self):
        return f"<FlowRun(id={self.id}, entity_type={self.entity_type}, status={self.status})>"
