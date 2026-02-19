"""Person identification model for document and identification information.

This table is designed for future use in the Employee module and other modules
that require detailed identification information. It's separated from the User
model to optimize database space and allow for future expansion.

Note: This table will be populated primarily by the Employee module.
For now, it's created as a placeholder for future development.
"""

from datetime import UTC, datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Column, Enum, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class DocumentType(PyEnum):
    """Types of identification documents."""

    DNI = "dni"  # Documento Nacional de Identidad
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    TAX_ID = "tax_id"
    OTHER = "other"


class EntityType(PyEnum):
    """Types of entities that can have identification information."""

    USER = "user"
    EMPLOYEE = "employee"
    CONTACT = "contact"


class PersonIdentification(Base):
    """Person identification model for document and identification information.

    This model is designed to be used by:
    - Employee module (primary use case)
    - User module (optional, for extended identification)
    - Contact module (for business contacts)

    Note: This table is separated from User to optimize database space
    and allow for future expansion in the Employee module.
    """

    __tablename__ = "person_identifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Polymorphic relationship
    entity_type = Column(
        Enum(EntityType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Identification information
    document_type = Column(
        Enum(DocumentType, native_enum=False, length=50),
        nullable=True,
    )
    document_number = Column(String(100), nullable=True, index=True)
    tax_id = Column(String(100), nullable=True)  # Número de identificación fiscal
    social_security_number = Column(String(100), nullable=True)  # Número de seguridad social

    # Additional identification fields (for future expansion)
    issuing_country = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    issuing_date = Column(TIMESTAMP(timezone=True), nullable=True)
    expiration_date = Column(TIMESTAMP(timezone=True), nullable=True)
    issuing_authority = Column(String(255), nullable=True)  # Autoridad emisora

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

    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_person_identifications_entity", "entity_type", "entity_id"),
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "document_type",
            "document_number",
            name="uq_person_identifications_entity_document",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<PersonIdentification(id={self.id}, entity_type={self.entity_type}, "
            f"document_type={self.document_type}, document_number={self.document_number})>"
        )
