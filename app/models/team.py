"""Team models for team and group management."""

from datetime import UTC, datetime
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
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class Team(Base):
    """Team model for group management."""

    __tablename__ = "teams"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Team information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Jerarquía (opcional para equipos anidados)
    parent_team_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Metadata
    color = Column(String(7), nullable=True)  # Hex color
    team_metadata = Column("metadata", JSONB, nullable=True)  # Usar alias para evitar conflicto
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    parent_team = relationship("Team", remote_side=[id], back_populates="child_teams")
    child_teams = relationship("Team", back_populates="parent_team")

    __table_args__ = (
        Index("idx_teams_tenant", "tenant_id", "is_active"),
        Index("idx_teams_parent", "tenant_id", "parent_team_id"),
    )

    def __repr__(self) -> str:
        return f"<Team(id={self.id}, name={self.name})>"


class TeamMember(Base):
    """Team member model for user-team relationships."""

    __tablename__ = "team_members"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Rol en el equipo (opcional)
    role = Column(String(50), nullable=True)  # "member", "leader", "admin"

    # Auditoría
    added_by = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    added_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

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

    # Relationships
    team = relationship("Team", back_populates="members")

    __table_args__ = (
        Index("idx_team_members_team", "tenant_id", "team_id"),
        Index("idx_team_members_user", "tenant_id", "user_id"),
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )

    def __repr__(self) -> str:
        return f"<TeamMember(id={self.id}, team_id={self.team_id}, user_id={self.user_id})>"
