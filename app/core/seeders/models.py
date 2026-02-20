"""Models for seeder tracking."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Column, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.core.db.session import Base


class SeederRecord(Base):
    """Model to track executed seeders."""

    __tablename__ = "seeders"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    seeder_name = Column(String(255), nullable=False, unique=True, index=True)
    executed_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("seeder_name", name="uq_seeders_name"),)

    def __repr__(self) -> str:
        return f"<SeederRecord(seeder_name={self.seeder_name}, executed_at={self.executed_at})>"
