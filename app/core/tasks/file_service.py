"""Task File Service for managing task file attachments.

Sprint 3 - Fase 2: Files Integration
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

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

        print("[SERVICE] attach_file called with:", flush=True)
        print(f"  task_id: {task_id}", flush=True)
        print(f"  tenant_id: {tenant_id}", flush=True)
        print(f"  user_id: {user_id}", flush=True)
        print(f"  file_id: {file_id}", flush=True)
        print(f"  file_name: {file_name}", flush=True)

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        print(f"[SERVICE] Task found: {task is not None}", flush=True)

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

        print(f"[SERVICE] Current metadata: {metadata}", flush=True)
        print(f"[SERVICE] Current attached_files count: {len(attached_files)}", flush=True)

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

        print("[SERVICE] After adding file:", flush=True)
        print(f"  New attached_files count: {len(attached_files)}", flush=True)
        print(f"  New metadata: {metadata}", flush=True)

        # Actualizar tarea
        task.task_metadata = metadata
        flag_modified(task, "task_metadata")
        print(f"[SERVICE] Setting task.task_metadata to: {metadata}", flush=True)

        self.db.commit()
        print("[SERVICE] Database committed", flush=True)

        self.db.refresh(task)
        print("[SERVICE] Task refreshed", flush=True)
        print(f"[SERVICE] Task.task_metadata after refresh: {task.task_metadata}", flush=True)

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

        print("\n[SERVICE] detach_file called with:", flush=True)
        print(f"  task_id: {task_id}", flush=True)
        print(f"  tenant_id: {tenant_id}", flush=True)
        print(f"  user_id: {user_id}", flush=True)
        print(f"  file_id: {file_id}", flush=True)

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        print(f"[SERVICE] Task found: {task is not None}", flush=True)

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

        print(f"[SERVICE] Current attached_files count: {len(attached_files)}", flush=True)
        if attached_files:
            print(f"[SERVICE] First file: {attached_files[0]}", flush=True)

        # Filtrar archivo a eliminar
        file_id_str = str(file_id)
        new_files = []
        for item in attached_files:
            if isinstance(item, dict):
                item_file_id = item.get("file_id")
                if item_file_id is not None and str(item_file_id) == file_id_str:
                    continue
            new_files.append(item)

        print(f"[SERVICE] After filtering, new_files count: {len(new_files)}", flush=True)

        if len(new_files) == len(attached_files):
            # No se encontró el archivo
            print("[SERVICE] File not found in attached_files", flush=True)
            return False

        file_record = self.db.query(File).filter(
            File.id == file_id,
            File.tenant_id == tenant_id,
        ).first()

        if not file_record:
            print("[SERVICE] File record not found for soft delete", flush=True)
        elif file_record.deleted_at is None:
            file_record.is_current = False
            file_record.deleted_at = datetime.now(UTC)
            print("[SERVICE] File soft delete applied", flush=True)
        else:
            print("[SERVICE] File already soft deleted", flush=True)

        metadata["attached_files"] = new_files
        task.task_metadata = metadata
        flag_modified(task, "task_metadata")

        print("[SERVICE] Committing to database...", flush=True)
        self.db.commit()
        print("[SERVICE] Database committed successfully", flush=True)

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

        print("\n[SERVICE] list_files called with:", flush=True)
        print(f"  task_id: {task_id}", flush=True)
        print(f"  tenant_id: {tenant_id}", flush=True)

        # Consulta SQL directa para depurar
        from sqlalchemy import text

        # Primero, verificar si hay tareas con archivos
        all_tasks = self.db.execute(text("""
            SELECT id, title, metadata
            FROM tasks
            WHERE tenant_id = :tenant_id
            AND metadata IS NOT NULL
            AND metadata->>'attached_files' IS NOT NULL
            LIMIT 5
        """), {"tenant_id": str(tenant_id)}).fetchall()

        print(f"[SERVICE] Tasks with files in tenant: {len(all_tasks)}", flush=True)
        for t in all_tasks:
            print(f"  Task {t[0]}: {t[1]} has metadata: {t[2]}", flush=True)

        sql_result = self.db.execute(text("""
            SELECT id, title, metadata
            FROM tasks
            WHERE id = :task_id AND tenant_id = :tenant_id
        """), {"task_id": str(task_id), "tenant_id": str(tenant_id)}).fetchone()

        print(f"[SERVICE] SQL result for specific task: {sql_result}", flush=True)
        if sql_result:
            print(f"[SERVICE] SQL metadata: {sql_result[2]}", flush=True)

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        print(f"[SERVICE] Task found: {task is not None}", flush=True)
        if task:
            print(f"[SERVICE] Task.task_metadata: {task.task_metadata}", flush=True)

        if not task:
            print("[SERVICE] Task not found, returning empty list", flush=True)
            return []

        metadata = task.task_metadata or {}
        attached_files = metadata.get("attached_files", [])

        print(f"[SERVICE] metadata: {metadata}", flush=True)
        print(f"[SERVICE] attached_files: {attached_files}", flush=True)
        print(f"[SERVICE] returning {len(attached_files)} files", flush=True)

        return attached_files


def get_task_file_service(db: Session) -> TaskFileService:
    """Obtener instancia del servicio de archivos.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskFileService
    """
    return TaskFileService(db)
