"""Automation models for rule-based automation engine."""

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class AutomationExecutionStatus(str, Enum):
    """Status of automation execution."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # Condition not met


class Rule(Base):
    """Rule model for automation rules."""

    __tablename__ = "rules"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    trigger = Column(JSONB, nullable=False)  # Event or time trigger config
    conditions = Column(JSONB, nullable=True)  # Array of condition objects
    actions = Column(JSONB, nullable=False)  # Array of action objects
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
    versions = relationship("RuleVersion", back_populates="rule", cascade="all, delete-orphan")
    executions = relationship(
        "AutomationExecution", back_populates="rule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_rules_tenant_enabled", "tenant_id", "enabled"),
    )


class RuleVersion(Base):
    """Rule version model for versioning automation rules."""

    __tablename__ = "rule_versions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    definition = Column(JSONB, nullable=False)  # Full rule definition snapshot
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    rule = relationship("Rule", back_populates="versions")

    __table_args__ = (
        Index("idx_rule_versions_rule_version", "rule_id", "version", unique=True),
    )


class AutomationExecution(Base):
    """Automation execution model for tracking rule executions."""

    __tablename__ = "automation_executions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    rule_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_id = Column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )  # ID of triggering event (for idempotency)
    status = Column(
        String(20), nullable=False, default=AutomationExecutionStatus.SUCCESS, index=True
    )
    result = Column(JSONB, nullable=True)  # Execution result data
    error_message = Column(Text, nullable=True)
    executed_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Relationships
    rule = relationship("Rule", back_populates="executions")

    __table_args__ = (
        Index("idx_automation_executions_event_id", "event_id", unique=True),
        Index("idx_automation_executions_rule_status", "rule_id", "status"),
        Index("idx_automation_executions_executed_at", "executed_at"),
    )









