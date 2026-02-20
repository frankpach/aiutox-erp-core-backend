"""ModuleRole model for internal module roles (e.g., inventory.editor, products.viewer)."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class ModuleRole(Base):
    """ModuleRole model for internal module roles assignment."""

    __tablename__ = "module_roles"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    module = Column(String(100), nullable=False)  # "inventory", "products", etc.
    role_name = Column(
        String(100), nullable=False
    )  # "editor", "viewer", "manager", etc.
    granted_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="module_roles", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint(
            "user_id", "module", "role_name", name="uq_module_roles_user_module_role"
        ),
        Index("idx_module_roles_user_module", "user_id", "module"),
    )

    def __repr__(self) -> str:
        return f"<ModuleRole(id={self.id}, user_id={self.user_id}, module={self.module}, role_name={self.role_name})>"
