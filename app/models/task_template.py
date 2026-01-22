"""Task Template model for standardized task processes."""

from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class TaskTemplate(Base):
    """
    Plantilla de tareas para procesos estandarizados.

    Permite definir plantillas reutilizables con checklist predefinido,
    tiempo estimado y estado por defecto.
    """

    __tablename__ = "task_templates"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # "Gestión de Llamada Proveedores"
    description = Column(Text(), nullable=True)
    estimated_hours = Column(Integer(), nullable=True)
    default_status_id = Column(PG_UUID(as_uuid=True), ForeignKey("task_statuses.id", ondelete="SET NULL"), nullable=True)
    checklist_items = Column(JSONB(), nullable=True)  # [{"text": "Llamar", "order": 1}, ...]
    created_by_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relaciones
    default_status = relationship("TaskStatus", back_populates="templates_default")
    creator = relationship("User", back_populates="created_templates")
    tasks = relationship("Task", back_populates="template")

    def __repr__(self) -> str:
        return f"<TaskTemplate(id={self.id}, name='{self.name}')>"
