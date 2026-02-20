"""Task File Service for managing task file attachments.

Sprint 3 - Fase 2: Files Integration
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.exceptions import APIException
from app.core.logging import get_logger
from app.core.pubsub import get_event_publisher
from app.core.pubsub.models import EventMetadata

logger = get_logger(__name__)

# Constantes de validación
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_FILE_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/plain",
    "text/csv",
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
]


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

    def _validate_file_params(
        self,
        file_url: str,
        file_size: int,
        file_type: str,
    ) -> None:
        """Validar parámetros de archivo.

        Args:
            file_url: URL del archivo
            file_size: Tamaño del archivo en bytes
            file_type: Tipo MIME del archivo

        Raises:
            APIException: Si algún parámetro es inválido
        """
        from app.core.security.url_validator import validate_file_url

        # SSRF protection
        validate_file_url(file_url)

        # Size validation
        if file_size <= 0:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_FILE_SIZE",
                message="File size must be greater than 0",
            )

        if file_size > MAX_FILE_SIZE:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="FILE_TOO_LARGE",
                message=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE} bytes",
            )

        # Type validation
        if file_type not in ALLOWED_FILE_TYPES:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_FILE_TYPE",
                message=f"File type {file_type} is not allowed. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}",
            )

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

        logger.debug(
            "Attaching file to task: task_id=%s, tenant_id=%s, user_id=%s, file_id=%s, file_name=%s",
            task_id,
            tenant_id,
            user_id,
            file_id,
            file_name,
        )

        # Validar parámetros ANTES de cualquier operación
        self._validate_file_params(file_url, file_size, file_type)

        task = (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

        logger.debug("Task found: %s", task is not None)

        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Obtener metadata actual
        metadata = dict(task.task_metadata or {})
        attached_files = metadata.get("attached_files", [])
        if not isinstance(attached_files, list):
            logger.warning(
                "Invalid attached_files type on task %s: %s",
                task_id,
                type(attached_files).__name__,
            )
            attached_files = []

        logger.debug("Current attached_files count: %d", len(attached_files))

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

        logger.debug("New attached_files count: %d", len(attached_files))

        # Actualizar tarea
        task.task_metadata = metadata
        flag_modified(task, "task_metadata")

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
        from app.models.file import File
        from app.models.task import Task

        logger.debug(
            "Detaching file from task: task_id=%s, tenant_id=%s, user_id=%s, file_id=%s",
            task_id,
            tenant_id,
            user_id,
            file_id,
        )

        task = (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

        logger.debug("Task found: %s", task is not None)

        if not task:
            return False

        # Obtener metadata actual
        metadata = dict(task.task_metadata or {})
        attached_files = metadata.get("attached_files", [])
        if not isinstance(attached_files, list):
            logger.warning(
                "Invalid attached_files type on task %s: %s",
                task_id,
                type(attached_files).__name__,
            )
            attached_files = []

        logger.debug("Current attached_files count: %d", len(attached_files))

        # Filtrar archivo a eliminar
        file_id_str = str(file_id)
        new_files = []
        for item in attached_files:
            if isinstance(item, dict):
                item_file_id = item.get("file_id")
                if item_file_id is not None and str(item_file_id) == file_id_str:
                    continue
            new_files.append(item)

        logger.debug("After filtering, new_files count: %d", len(new_files))

        if len(new_files) == len(attached_files):
            # No se encontró el archivo
            logger.debug("File not found in attached_files")
            return False

        file_record = (
            self.db.query(File)
            .filter(
                File.id == file_id,
                File.tenant_id == tenant_id,
            )
            .first()
        )

        if not file_record:
            logger.debug("File record not found for soft delete")
        elif file_record.deleted_at is None:
            file_record.is_current = False
            file_record.deleted_at = datetime.now(UTC)
            logger.debug("File soft delete applied")
        else:
            logger.debug("File already soft deleted")

        metadata["attached_files"] = new_files
        task.task_metadata = metadata
        flag_modified(task, "task_metadata")

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

        logger.debug(
            "Listing files for task: task_id=%s, tenant_id=%s", task_id, tenant_id
        )

        task = (
            self.db.query(Task)
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

        if not task:
            logger.debug("Task not found, returning empty list")
            return []

        metadata = task.task_metadata or {}
        attached_files = metadata.get("attached_files", [])

        logger.debug("Returning %d files for task %s", len(attached_files), task_id)

        return attached_files


def get_task_file_service(db: Session) -> TaskFileService:
    """Obtener instancia del servicio de archivos.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskFileService
    """
    return TaskFileService(db)
