"""Contact method model for polymorphic contact information."""

from datetime import UTC, datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import Boolean, Column, Enum, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class ContactMethodType(PyEnum):
    """Types of contact methods."""

    EMAIL = "email"
    PHONE = "phone"
    MOBILE = "mobile"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    ADDRESS = "address"
    WEBSITE = "website"
    FAX = "fax"


class EntityType(PyEnum):
    """Types of entities that can have contact methods."""

    USER = "user"
    CONTACT = "contact"
    ORGANIZATION = "organization"
    EMPLOYEE = "employee"
    TENANT = "tenant"


class ContactMethod(Base):
    """Contact method model for polymorphic contact information."""

    __tablename__ = "contact_methods"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Polymorphic relationship
    entity_type = Column(
        Enum(EntityType, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    entity_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Contact method details
    method_type = Column(
        Enum(ContactMethodType, native_enum=False, length=50),
        nullable=False,
    )
    value = Column(String(500), nullable=False)  # The actual contact value

    # Address fields (only used when method_type = ADDRESS)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2

    # Metadata
    label = Column(String(100), nullable=True)  # e.g., "Trabajo", "Personal", "Casa"
    is_primary = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(TIMESTAMP(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

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
        Index("ix_contact_methods_entity", "entity_type", "entity_id"),
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "method_type",
            "value",
            name="uq_contact_methods_entity_type_value",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<ContactMethod(id={self.id}, entity_type={self.entity_type}, "
            f"method_type={self.method_type}, value={self.value[:30]}...)>"
        )
