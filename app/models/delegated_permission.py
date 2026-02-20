"""DelegatedPermission model for user-specific permission delegation."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class DelegatedPermission(Base):
    """DelegatedPermission model for permission delegation by module leaders."""

    __tablename__ = "delegated_permissions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    module = Column(String(100), nullable=False)  # "inventory", "products", etc.
    permission = Column(
        String(255), nullable=False
    )  # "inventory.edit", "products.view", etc.
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    user = relationship(
        "User", back_populates="delegated_permissions", foreign_keys=[user_id]
    )
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "module",
            "permission",
            "granted_by",
            name="uq_delegated_permissions_user_module_permission_granter",
        ),
        Index("idx_delegated_permissions_user_id", "user_id"),
        Index("idx_delegated_permissions_granted_by", "granted_by"),
        # Note: Partial index for active permissions will be created in migration
        # Index idx_delegated_permissions_active WHERE revoked_at IS NULL
    )

    @property
    def is_active(self) -> bool:
        """
        Check if permission is currently active.

        Active = not revoked AND (not expired OR no expiration date).

        Returns:
            True if permission is active, False otherwise.
        """
        if self.revoked_at is not None:
            return False
        if self.expires_at is None:
            return True
        return self.expires_at > datetime.now(UTC)

    def __repr__(self) -> str:
        return (
            f"<DelegatedPermission(id={self.id}, user_id={self.user_id}, "
            f"module={self.module}, permission={self.permission}, "
            f"granted_by={self.granted_by})>"
        )
