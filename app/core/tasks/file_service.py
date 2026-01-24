"""Task File Service for managing task file attachments.

Sprint 3 - Fase 2: Files Integration
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.pubsub import get_event_publisher
from app.core.pubsub.models import EventMetadata

logger = get_logger(__name__)


class TaskFileService:
    """Servicio para gestión de archivos adjuntos en tareas."""

    def __init__(self, db: Session, event_publisher: Any | None = None):
        """Inicializar servicio de archivos.

        Args:
            db: Sesión de base de datos
            event_publisher: Publicador de eventos (opcional)
        """
        self.db = db
        self.event_publisher = event_publisher or get_event_publisher()

    def attach_file(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        file_id: UUID,
        file_name: str,
        file_size: int,
        file_type: str,
        file_url: str,
    ) -> dict[str, Any]:
        """Adjuntar archivo a una tarea.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario
            file_id: ID del archivo en el sistema de files
            file_name: Nombre del archivo
            file_size: Tamaño del archivo en bytes
            file_type: Tipo MIME del archivo
            file_url: URL del archivo

        Returns:
            Diccionario con información del archivo adjunto
        """
        from app.models.task import Task

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Obtener metadata actual
        metadata = task.task_metadata or {}
        attached_files = metadata.get("attached_files", [])

        # Agregar nuevo archivo
        file_attachment = {
            "file_id": str(file_id),
            "file_name": file_name,
            "file_size": file_size,
            "file_type": file_type,
            "file_url": file_url,
            "attached_at": datetime.now(UTC).isoformat(),
            "attached_by": str(user_id),
        }

        attached_files.append(file_attachment)
        metadata["attached_files"] = attached_files

        # Actualizar tarea
        task.task_metadata = metadata
        self.db.commit()
        self.db.refresh(task)

        # Publicar evento
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.file_attached",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_file_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                    "file_id": str(file_id),
                    "file_name": file_name,
                    "file_size": file_size,
                    "file_type": file_type,
                },
            ),
        )

        logger.info(f"File {file_id} attached to task {task_id}")

        return file_attachment

    def detach_file(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        file_id: UUID,
    ) -> bool:
        """Desadjuntar archivo de una tarea.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario
            file_id: ID del archivo

        Returns:
            True si se desadjuntó correctamente
        """
        from app.models.task import Task

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        if not task:
            return False

        # Obtener metadata actual
        metadata = task.task_metadata or {}
        attached_files = metadata.get("attached_files", [])

        # Filtrar archivo a eliminar
        file_id_str = str(file_id)
        new_files = [f for f in attached_files if f.get("file_id") != file_id_str]

        if len(new_files) == len(attached_files):
            # No se encontró el archivo
            return False

        metadata["attached_files"] = new_files
        task.task_metadata = metadata
        self.db.commit()

        # Publicar evento
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.file_removed",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_file_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                    "file_id": str(file_id),
                },
            ),
        )

        logger.info(f"File {file_id} detached from task {task_id}")

        return True

    def list_files(
        self,
        task_id: UUID,
        tenant_id: UUID,
    ) -> list[dict[str, Any]]:
        """Listar archivos adjuntos de una tarea.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant

        Returns:
            Lista de archivos adjuntos
        """
        from app.models.task import Task

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        if not task:
            return []

        metadata = task.task_metadata or {}
        return metadata.get("attached_files", [])


def get_task_file_service(db: Session) -> TaskFileService:
    """Obtener instancia del servicio de archivos.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskFileService
    """
    return TaskFileService(db)
