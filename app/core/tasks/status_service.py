"""Task Status Service for managing customizable task statuses.

Sprint 2 - Fase 2: Estados Customizables UI
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.task_status import TaskStatus

logger = get_logger(__name__)


class TaskStatusService:
    """Servicio para gestión de estados de tareas personalizables."""

    def __init__(self, db: Session):
        """Inicializar servicio de estados.

        Args:
            db: Sesión de base de datos
        """
        self.db = db

    def get_statuses(self, tenant_id: UUID) -> list[TaskStatus]:
        """Obtener todos los estados de un tenant.

        Args:
            tenant_id: ID del tenant

        Returns:
            Lista de estados ordenados
        """
        return (
            self.db.query(TaskStatus)
            .filter(TaskStatus.tenant_id == tenant_id)
            .order_by(TaskStatus.order, TaskStatus.name)
            .all()
        )

    def get_status_by_id(self, status_id: UUID, tenant_id: UUID) -> TaskStatus | None:
        """Obtener estado por ID.

        Args:
            status_id: ID del estado
            tenant_id: ID del tenant

        Returns:
            Estado o None si no existe
        """
        return (
            self.db.query(TaskStatus)
            .filter(TaskStatus.id == status_id, TaskStatus.tenant_id == tenant_id)
            .first()
        )

    def create_status(
        self,
        tenant_id: UUID,
        name: str,
        status_type: str,
        color: str,
        order: int = 0,
    ) -> TaskStatus:
        """Crear nuevo estado personalizado.

        Args:
            tenant_id: ID del tenant
            name: Nombre del estado
            status_type: Tipo de estado (open, in_progress, closed)
            color: Color en formato hex
            order: Orden de visualización

        Returns:
            Estado creado
        """
        status = TaskStatus(
            tenant_id=tenant_id,
            name=name,
            type=status_type,
            color=color,
            order=order,
            is_system=False,
        )

        self.db.add(status)
        self.db.commit()
        self.db.refresh(status)

        logger.info(f"Task status created: {status.id} ({name}) for tenant {tenant_id}")

        return status

    def update_status(
        self,
        status_id: UUID,
        tenant_id: UUID,
        update_data: dict,
    ) -> TaskStatus | None:
        """Actualizar estado existente.

        Args:
            status_id: ID del estado
            tenant_id: ID del tenant
            update_data: Datos a actualizar

        Returns:
            Estado actualizado o None si no existe o es de sistema
        """
        status = self.get_status_by_id(status_id, tenant_id)
        if not status:
            return None

        # No permitir editar estados del sistema
        if status.is_system:
            logger.warning(f"Attempted to update system status {status_id}")
            return None

        for key, value in update_data.items():
            if hasattr(status, key) and value is not None:
                setattr(status, key, value)

        self.db.commit()
        self.db.refresh(status)

        logger.info(f"Task status updated: {status_id}")

        return status

    def delete_status(self, status_id: UUID, tenant_id: UUID) -> bool:
        """Eliminar estado personalizado.

        Args:
            status_id: ID del estado
            tenant_id: ID del tenant

        Returns:
            True si se eliminó correctamente
        """
        status = self.get_status_by_id(status_id, tenant_id)
        if not status:
            return False

        # No permitir eliminar estados del sistema
        if status.is_system:
            logger.warning(f"Attempted to delete system status {status_id}")
            return False

        # Verificar si hay tareas usando este estado
        from app.models.task import Task

        tasks_count = (
            self.db.query(Task)
            .filter(Task.status_id == status_id, Task.tenant_id == tenant_id)
            .count()
        )

        if tasks_count > 0:
            logger.warning(
                f"Cannot delete status {status_id}: {tasks_count} tasks are using it"
            )
            return False

        self.db.delete(status)
        self.db.commit()

        logger.info(f"Task status deleted: {status_id}")

        return True

    def reorder_statuses(
        self, tenant_id: UUID, status_orders: dict[UUID, int]
    ) -> list[TaskStatus]:
        """Reordenar estados.

        Args:
            tenant_id: ID del tenant
            status_orders: Diccionario {status_id: new_order}

        Returns:
            Lista de estados actualizados
        """
        statuses = []

        for status_id, new_order in status_orders.items():
            status = self.get_status_by_id(status_id, tenant_id)
            if status:
                status.order = new_order
                statuses.append(status)

        self.db.commit()

        logger.info(f"Reordered {len(statuses)} statuses for tenant {tenant_id}")

        return self.get_statuses(tenant_id)

    def initialize_default_statuses(self, tenant_id: UUID) -> list[TaskStatus]:
        """Inicializar estados por defecto para un nuevo tenant.

        Args:
            tenant_id: ID del tenant

        Returns:
            Lista de estados creados
        """
        default_statuses = [
            {"name": "Por Hacer", "type": "open", "color": "#9E9E9E", "order": 0},
            {"name": "En Progreso", "type": "in_progress", "color": "#2196F3", "order": 1},
            {"name": "En Espera", "type": "in_progress", "color": "#FF9800", "order": 2},
            {"name": "Bloqueado", "type": "in_progress", "color": "#F44336", "order": 3},
            {"name": "En Revisión", "type": "in_progress", "color": "#9C27B0", "order": 4},
            {"name": "Completado", "type": "closed", "color": "#4CAF50", "order": 5},
            {"name": "Cancelado", "type": "closed", "color": "#607D8B", "order": 6},
        ]

        statuses = []

        for status_data in default_statuses:
            status = TaskStatus(
                tenant_id=tenant_id,
                name=status_data["name"],
                type=status_data["type"],
                color=status_data["color"],
                order=status_data["order"],
                is_system=True,
            )
            self.db.add(status)
            statuses.append(status)

        self.db.commit()

        logger.info(f"Initialized {len(statuses)} default statuses for tenant {tenant_id}")

        return statuses


def get_task_status_service(db: Session) -> TaskStatusService:
    """Obtener instancia del servicio de estados.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskStatusService
    """
    return TaskStatusService(db)
