"""Task Status model for customizable task statuses."""

from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class TaskStatus(Base):
    """
    Estado de tarea personalizable por tenant.

    Cada tenant puede tener estados base del sistema (no eliminables) y estados
    personalizados. Los estados se agrupan por tipo: open, in_progress, closed.
    """

    __tablename__ = "task_statuses"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(50), nullable=False)  # "Vendido", "Llamado", "Por Iniciar"
    type = Column(
        String(20), nullable=False, index=True
    )  # "open", "closed", "in_progress"
    color = Column(String(7), nullable=False)  # "#FF5722"
    is_system = Column(
        Boolean, default=False, nullable=False
    )  # Estados base no eliminables
    order = Column(Integer, default=0, nullable=False)

    # Relaciones
    tasks = relationship(
        "Task", back_populates="status_obj", foreign_keys="Task.status_id"
    )
    templates_default = relationship("TaskTemplate", back_populates="default_status")

    def __repr__(self) -> str:
        return f"<TaskStatus(id={self.id}, name='{self.name}', type='{self.type}')>"
