"""Task resource model for managing task resources."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.base_class import Base


class TaskResource(Base):
    """Recurso asignado a tarea (usuario o equipo)."""

    __tablename__ = "task_resources"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    resource_type = Column(String(20), nullable=False)  # "user", "team"
    resource_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    allocated_hours = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relaciones
    task = relationship("Task", backref="resources")

    def __repr__(self) -> str:
        return f"<TaskResource(id={self.id}, task_id={self.task_id}, resource_type={self.resource_type})>"
