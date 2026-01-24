"""Task dependency model for managing task dependencies."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.base_class import Base


class TaskDependency(Base):
    """Dependencia entre tareas."""

    __tablename__ = "task_dependencies"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    task_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    depends_on_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    dependency_type = Column(String(20), nullable=False, default="finish_to_start")

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relaciones
    task = relationship("Task", foreign_keys=[task_id], backref="dependencies")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_id], backref="dependent_tasks")

    __table_args__ = (
        UniqueConstraint('task_id', 'depends_on_id', name='uq_task_dependency'),
    )

    def __repr__(self) -> str:
        return f"<TaskDependency(id={self.id}, task_id={self.task_id}, depends_on_id={self.depends_on_id})>"
