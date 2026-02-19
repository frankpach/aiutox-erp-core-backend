"""Organization model for business entities (customers, suppliers, partners)."""

from datetime import UTC, datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class OrganizationType(PyEnum):
    """Types of business organizations."""

    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PARTNER = "partner"
    OTHER = "other"


class Organization(Base):
    """Organization model for business entities (customers, suppliers, partners)."""

    __tablename__ = "organizations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255), nullable=True)  # Razón social
    tax_id = Column(String(100), nullable=True, index=True)  # NIT, RUC, etc.
    organization_type = Column(
        String(50), nullable=False, index=True
    )  # customer, supplier, partner, other
    industry = Column(String(100), nullable=True)  # Industria/sector
    website = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)  # Notas internas
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
    tenant = relationship("Tenant", backref="organizations")
    contacts = relationship("Contact", back_populates="organization", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_organizations_tenant_type", "tenant_id", "organization_type"),
        UniqueConstraint("tenant_id", "tax_id", name="uq_organizations_tenant_tax_id"),
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"
