"""Approval models for approval workflow management."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class ApprovalFlowType(str, Enum):
    """Approval flow types."""

    SEQUENTIAL = "sequential"  # One approver after another
    PARALLEL = "parallel"  # All approvers at once
    CONDITIONAL = "conditional"  # Conditional based on rules


class ApprovalStatus(str, Enum):
    """Approval request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    DELEGATED = "delegated"


class ApprovalActionType(str, Enum):
    """Approval action types."""

    APPROVE = "approve"
    REJECT = "reject"
    DELEGATE = "delegate"
    COMMENT = "comment"


class ApprovalFlow(Base):
    """Approval flow model for configurable approval workflows."""

    __tablename__ = "approval_flows"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Flow information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    flow_type = Column(String(20), nullable=False)  # sequential, parallel, conditional
    module = Column(String(50), nullable=False, index=True)  # e.g., 'products', 'orders'

    # Configuration
    conditions = Column(JSONB, nullable=True)  # Conditional rules for flow
    is_active = Column(Boolean, default=True, nullable=False)

    # Ownership
    created_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

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
    steps = relationship("ApprovalStep", back_populates="flow", cascade="all, delete-orphan")
    requests = relationship("ApprovalRequest", back_populates="flow")

    __table_args__ = (
        Index("idx_approval_flows_tenant_module", "tenant_id", "module"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalFlow(id={self.id}, name={self.name}, type={self.flow_type})>"


class ApprovalStep(Base):
    """Approval step model for workflow steps."""

    __tablename__ = "approval_steps"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Flow relationship
    flow_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_flows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Step information
    step_order = Column(Integer, nullable=False)  # Order in the flow
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Approver configuration
    approver_type = Column(String(20), nullable=False)  # user, role, dynamic
    approver_id = Column(PG_UUID(as_uuid=True), nullable=True)  # User or role ID
    approver_role = Column(String(50), nullable=True)  # Role name if approver_type is role
    approver_rule = Column(JSONB, nullable=True)  # Dynamic approver rule

    # Requirements
    require_all = Column(Boolean, default=False, nullable=False)  # Require all approvers (for parallel)
    min_approvals = Column(Integer, nullable=True)  # Minimum approvals required

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
    flow = relationship("ApprovalFlow", back_populates="steps")

    __table_args__ = (
        Index("idx_approval_steps_flow_order", "flow_id", "step_order"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalStep(id={self.id}, flow_id={self.flow_id}, order={self.step_order})>"


class ApprovalRequest(Base):
    """Approval request model for tracking approval requests."""

    __tablename__ = "approval_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Flow relationship
    flow_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_flows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Request information
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Entity relationship (polymorphic)
    entity_type = Column(String(50), nullable=False, index=True)  # e.g., 'order', 'invoice'
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Status
    status = Column(String(20), nullable=False, default=ApprovalStatus.PENDING, index=True)
    current_step = Column(Integer, default=1, nullable=False)  # Current step in flow

    # Requester
    requested_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    request_metadata = Column("metadata", JSONB, nullable=True)

    # Timestamps
    requested_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
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
    flow = relationship("ApprovalFlow", back_populates="requests")
    actions = relationship("ApprovalAction", back_populates="request", cascade="all, delete-orphan")
    delegations = relationship("ApprovalDelegation", back_populates="request", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_approval_requests_entity", "entity_type", "entity_id"),
        Index("idx_approval_requests_status", "tenant_id", "status"),
        Index("idx_approval_requests_flow", "flow_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalRequest(id={self.id}, title={self.title}, status={self.status})>"


class ApprovalAction(Base):
    """Approval action model for tracking approval actions."""

    __tablename__ = "approval_actions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Request relationship
    request_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Action information
    action_type = Column(String(20), nullable=False)  # approve, reject, delegate, comment
    step_order = Column(Integer, nullable=False)  # Step where action was taken
    comment = Column(Text, nullable=True)

    # Actor
    acted_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    request_metadata = Column("metadata", JSONB, nullable=True)

    # Timestamps
    acted_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Relationships
    request = relationship("ApprovalRequest", back_populates="actions")

    __table_args__ = (
        Index("idx_approval_actions_request", "request_id", "acted_at"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalAction(id={self.id}, request_id={self.request_id}, type={self.action_type})>"


class ApprovalDelegation(Base):
    """Approval delegation model for temporary delegation of approvals."""

    __tablename__ = "approval_delegations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Request relationship
    request_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Delegation information
    from_user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Expiration
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)

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
    request = relationship("ApprovalRequest", back_populates="delegations")

    __table_args__ = (
        Index("idx_approval_delegations_active", "tenant_id", "is_active"),
        Index("idx_approval_delegations_from", "from_user_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ApprovalDelegation(id={self.id}, from={self.from_user_id}, to={self.to_user_id})>"


