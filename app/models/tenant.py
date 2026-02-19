"""Tenant model for multi-tenant architecture."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class Tenant(Base):
    """Tenant model for multi-tenant architecture."""

    __tablename__ = "tenants"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
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
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("slug", name="uq_tenants_slug"),)

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"
