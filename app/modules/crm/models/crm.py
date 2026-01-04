from __future__ import annotations

from datetime import UTC, datetime
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.core.db.session import Base


class Pipeline(Base):
    __tablename__ = "crm_pipelines"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)

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

    leads = relationship("Lead", back_populates="pipeline")
    opportunities = relationship("Opportunity", back_populates="pipeline")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_crm_pipelines_tenant_name"),
        Index("idx_crm_pipelines_tenant_name", "tenant_id", "name"),
    )


class Lead(Base):
    __tablename__ = "crm_leads"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    pipeline_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("crm_pipelines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    organization_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="new", index=True)
    source = Column(String(100), nullable=True)

    estimated_value = Column(Numeric(18, 6), nullable=True)
    probability = Column(Numeric(5, 2), nullable=True)

    assigned_to_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    next_event_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    notes = Column(Text, nullable=True)

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

    pipeline = relationship("Pipeline", back_populates="leads")

    __table_args__ = (
        Index("idx_crm_leads_tenant_status", "tenant_id", "status"),
    )


class Opportunity(Base):
    __tablename__ = "crm_opportunities"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    pipeline_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("crm_pipelines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    organization_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    contact_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    name = Column(String(255), nullable=False)
    stage = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="open", index=True)

    amount = Column(Numeric(18, 6), nullable=True)
    probability = Column(Numeric(5, 2), nullable=True)

    expected_close_date = Column(TIMESTAMP(timezone=True), nullable=True)

    assigned_to_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    next_event_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    notes = Column(Text, nullable=True)

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

    pipeline = relationship("Pipeline", back_populates="opportunities")

    __table_args__ = (
        Index("idx_crm_opportunities_tenant_status", "tenant_id", "status"),
    )
