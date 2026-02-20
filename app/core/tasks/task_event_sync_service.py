"""Task-Calendar Event Synchronization Service.

Servicio para sincronización bidireccional entre Tasks y Calendar Events.
Implementa la lógica de negocio para Sprint 1 - Fase 2.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.pubsub import get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.task import Task
from app.repositories.task_repository import TaskRepository

logger = get_logger(__name__)


class TaskEventSyncService:
    """Servicio para sincronización Tasks-Calendar Events."""

    def __init__(self, db: Session, event_publisher: Any | None = None):
        """Inicializar servicio de sincronización.

        Args:
            db: Sesión de base de datos
            event_publisher: Publicador de eventos (opcional)
        """
        self.db = db
        self.repository = TaskRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()

    async def sync_task_to_calendar(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        calendar_provider: str = "internal",
        calendar_id: str | None = None,
    ) -> dict[str, Any]:
        """Sincronizar tarea a calendario.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario
            calendar_provider: Proveedor de calendario (internal, google, outlook)
            calendar_id: ID del calendario destino (opcional)

        Returns:
            Diccionario con información de sincronización

        Raises:
            ValueError: Si la tarea no existe o no tiene fechas válidas
        """
        task = self.repository.get_task_by_id(task_id, tenant_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Validar que la tarea tenga fechas para sincronizar
        if not task.start_at and not task.due_date:
            raise ValueError("Task must have start_at or due_date to sync to calendar")

        # Crear evento de calendario
        event_data = self._task_to_calendar_event(task)

        # Guardar metadata de sincronización en la tarea
        sync_metadata = {
            "calendar_synced": True,
            "calendar_provider": calendar_provider,
            "calendar_id": calendar_id or "default",
            "synced_at": datetime.now(UTC).isoformat(),
            "synced_by": str(user_id),
        }

        # Actualizar metadata de la tarea
        current_metadata = task.task_metadata or {}
        current_metadata.update(sync_metadata)

        self.repository.update_task(
            task_id, tenant_id, {"task_metadata": current_metadata}
        )

        # Publicar evento de sincronización
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.calendar_synced",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_event_sync_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                    "calendar_provider": calendar_provider,
                    "calendar_id": calendar_id or "default",
                    "event_data": event_data,
                },
            ),
        )

        logger.info(f"Task {task_id} synced to calendar {calendar_provider}")

        return {
            "task_id": str(task_id),
            "calendar_provider": calendar_provider,
            "calendar_id": calendar_id or "default",
            "event_data": event_data,
            "synced_at": sync_metadata["synced_at"],
        }

    async def unsync_task_from_calendar(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Desincronizar tarea del calendario.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario

        Returns:
            True si se desincroniź correctamente
        """
        task = self.repository.get_task_by_id(task_id, tenant_id)
        if not task:
            return False

        # Remover metadata de sincronización
        current_metadata = task.task_metadata or {}
        sync_keys = [
            "calendar_synced",
            "calendar_provider",
            "calendar_id",
            "synced_at",
            "synced_by",
        ]
        for key in sync_keys:
            current_metadata.pop(key, None)

        self.repository.update_task(
            task_id, tenant_id, {"task_metadata": current_metadata}
        )

        # Publicar evento de desincronización
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.calendar_unsynced",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_event_sync_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                },
            ),
        )

        logger.info(f"Task {task_id} unsynced from calendar")
        return True

    async def update_calendar_event(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any] | None:
        """Actualizar evento de calendario cuando la tarea cambia.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario

        Returns:
            Diccionario con información de actualización o None si no está sincronizada
        """
        task = self.repository.get_task_by_id(task_id, tenant_id)
        if not task:
            return None

        # Verificar si la tarea está sincronizada
        metadata = task.task_metadata or {}
        if not metadata.get("calendar_synced"):
            return None

        # Crear evento actualizado
        event_data = self._task_to_calendar_event(task)

        # Actualizar timestamp de sincronización
        metadata["synced_at"] = datetime.now(UTC).isoformat()
        metadata["last_updated_by"] = str(user_id)

        self.repository.update_task(task_id, tenant_id, {"task_metadata": metadata})

        # Publicar evento de actualización
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.calendar_updated",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_event_sync_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                    "calendar_provider": metadata.get("calendar_provider"),
                    "event_data": event_data,
                },
            ),
        )

        logger.info(f"Calendar event updated for task {task_id}")

        return {
            "task_id": str(task_id),
            "calendar_provider": metadata.get("calendar_provider"),
            "event_data": event_data,
            "updated_at": metadata["synced_at"],
        }

    async def sync_batch_tasks(
        self,
        task_ids: list[UUID],
        tenant_id: UUID,
        user_id: UUID,
        calendar_provider: str = "internal",
        calendar_id: str | None = None,
    ) -> dict[str, Any]:
        """Sincronizar múltiples tareas a calendario.

        Args:
            task_ids: Lista de IDs de tareas
            tenant_id: ID del tenant
            user_id: ID del usuario
            calendar_provider: Proveedor de calendario
            calendar_id: ID del calendario destino

        Returns:
            Diccionario con resultados de sincronización
        """
        results = {
            "synced": [],
            "failed": [],
            "skipped": [],
        }

        for task_id in task_ids:
            try:
                result = await self.sync_task_to_calendar(
                    task_id=task_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    calendar_provider=calendar_provider,
                    calendar_id=calendar_id,
                )
                results["synced"].append(result)
            except ValueError as e:
                logger.warning(f"Skipped task {task_id}: {e}")
                results["skipped"].append(
                    {
                        "task_id": str(task_id),
                        "reason": str(e),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to sync task {task_id}: {e}")
                results["failed"].append(
                    {
                        "task_id": str(task_id),
                        "error": str(e),
                    }
                )

        logger.info(
            f"Batch sync completed: {len(results['synced'])} synced, "
            f"{len(results['skipped'])} skipped, {len(results['failed'])} failed"
        )

        return results

    def get_sync_status(
        self,
        task_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Obtener estado de sincronización de una tarea.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant

        Returns:
            Diccionario con estado de sincronización
        """
        task = self.repository.get_task_by_id(task_id, tenant_id)
        if not task:
            return {"synced": False, "error": "Task not found"}

        metadata = task.task_metadata or {}

        return {
            "synced": metadata.get("calendar_synced", False),
            "calendar_provider": metadata.get("calendar_provider"),
            "calendar_id": metadata.get("calendar_id"),
            "synced_at": metadata.get("synced_at"),
            "synced_by": metadata.get("synced_by"),
            "last_updated_by": metadata.get("last_updated_by"),
        }

    def _task_to_calendar_event(self, task: Task) -> dict[str, Any]:
        """Convertir tarea a formato de evento de calendario.

        Args:
            task: Tarea a convertir

        Returns:
            Diccionario con datos del evento
        """
        event = {
            "title": task.title,
            "description": task.description or "",
            "all_day": task.all_day,
        }

        # Fechas
        if task.start_at:
            event["start"] = task.start_at.isoformat()
        if task.end_at:
            event["end"] = task.end_at.isoformat()
        if task.due_date and not task.start_at:
            event["start"] = task.due_date.isoformat()
            event["end"] = task.due_date.isoformat()

        # Metadata adicional
        event["metadata"] = {
            "task_id": str(task.id),
            "priority": task.priority,
            "status": task.status,
            "source": "aiutox_tasks",
        }

        # Color override
        if task.color_override:
            event["color"] = task.color_override

        return event


def get_task_event_sync_service(db: Session) -> TaskEventSyncService:
    """Obtener instancia del servicio de sincronización.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskEventSyncService
    """
    return TaskEventSyncService(db)
