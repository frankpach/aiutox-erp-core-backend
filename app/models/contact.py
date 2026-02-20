"""Contact model for persons who are contacts of organizations."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class Contact(Base):
    """Contact model for persons who are contacts of organizations."""

    __tablename__ = "contacts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    middle_name = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)  # Calculado o almacenado
    job_title = Column(String(255), nullable=True)  # Cargo en la organización
    department = Column(String(255), nullable=True)  # Departamento
    is_primary_contact = Column(
        Boolean, default=False, nullable=False
    )  # Contacto principal
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
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
    tenant = relationship("Tenant", backref="contacts")
    organization = relationship("Organization", back_populates="contacts")

    # Indexes
    __table_args__ = (
        Index("ix_contacts_tenant_organization", "tenant_id", "organization_id"),
    )

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, full_name={self.full_name}, organization_id={self.organization_id})>"
