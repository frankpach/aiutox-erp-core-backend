"""User Calendar Preferences Model.

Sprint 5 - Fase 2: Preferencias de calendario por usuario
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.base_class import Base


class UserCalendarPreferences(Base):
    """Preferencias de calendario por usuario."""

    __tablename__ = "user_calendar_preferences"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Tenant ID
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sync settings
    auto_sync_tasks = Column(
        Boolean, nullable=False, default=False
    )  # Auto-sync tasks to calendar
    auto_sync_enabled = Column(Boolean, nullable=False, default=False)
    default_calendar_id = Column(
        PG_UUID(as_uuid=True), nullable=True
    )  # Default calendar for synced tasks
    default_calendar_provider = Column(
        String(50), nullable=False, default="internal"
    )  # internal, google, outlook

    # Configuración de tiempo
    timezone = Column(String(50), nullable=False, default="America/Mexico_City")
    time_format = Column(String(10), nullable=False, default="24h")  # 24h or 12h

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

    # Relaciones
    # user = relationship("User", back_populates="calendar_preferences")

    def __repr__(self) -> str:
        return f"<UserCalendarPreferences(user_id={self.user_id}, auto_sync={self.auto_sync_enabled})>"
