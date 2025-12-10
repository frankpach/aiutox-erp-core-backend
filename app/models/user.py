"""User model with authentication support."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class User(Base):
    """User model with authentication, tenant support, and personal information."""

    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Información personal básica
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    middle_name = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)  # Mantener para compatibilidad
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    nationality = Column(String(2), nullable=True)  # ISO 3166-1 alpha-2
    marital_status = Column(String(20), nullable=True)

    # Información laboral/profesional
    job_title = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    employee_id = Column(String(100), nullable=True, unique=True, index=True)

    # Preferencias y configuración
    preferred_language = Column(String(10), default="es", nullable=False)
    timezone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Campos adicionales de autenticación
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    email_verified_at = Column(TIMESTAMP(timezone=True), nullable=True)
    phone_verified_at = Column(TIMESTAMP(timezone=True), nullable=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)

    # Relación con tenant
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    global_roles = relationship(
        "UserRole", back_populates="user", foreign_keys="UserRole.user_id", cascade="all, delete-orphan"
    )
    module_roles = relationship(
        "ModuleRole", back_populates="user", foreign_keys="ModuleRole.user_id", cascade="all, delete-orphan"
    )
    delegated_permissions = relationship(
        "DelegatedPermission", back_populates="user", foreign_keys="DelegatedPermission.user_id", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    # Note: contact_methods relationship will be handled via ContactMethodRepository
    # due to polymorphic nature (entity_type + entity_id)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, tenant_id={self.tenant_id})>"

