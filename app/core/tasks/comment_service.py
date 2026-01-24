"""Task Comment Service for managing task comments and mentions.

Sprint 4 - Fase 2: Comments Integration
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.pubsub import get_event_publisher
from app.core.pubsub.models import EventMetadata

logger = get_logger(__name__)


class TaskCommentService:
    """Servicio para gestión de comentarios en tareas."""

    def __init__(self, db: Session, event_publisher: Any | None = None):
        """Inicializar servicio de comentarios.

        Args:
            db: Sesión de base de datos
            event_publisher: Publicador de eventos (opcional)
        """
        self.db = db
        self.event_publisher = event_publisher or get_event_publisher()

    def add_comment(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        content: str,
        mentions: list[UUID] | None = None,
    ) -> dict[str, Any]:
        """Agregar comentario a una tarea.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario
            content: Contenido del comentario
            mentions: Lista de IDs de usuarios mencionados

        Returns:
            Diccionario con información del comentario
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
        comments = metadata.get("comments", [])

        # Crear nuevo comentario
        comment_id = str(UUID())
        comment = {
            "id": comment_id,
            "content": content,
            "user_id": str(user_id),
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "mentions": [str(m) for m in mentions] if mentions else [],
        }

        comments.append(comment)
        metadata["comments"] = comments

        # Actualizar tarea
        task.task_metadata = metadata
        self.db.commit()
        self.db.refresh(task)

        # Publicar evento
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.comment_added",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_comment_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                    "comment_id": comment_id,
                    "mentions": comment["mentions"],
                },
            ),
        )

        # Si hay menciones, publicar eventos de notificación
        if mentions:
            for mentioned_user_id in mentions:
                safe_publish_event(
                    event_publisher=self.event_publisher,
                    event_type="task.user_mentioned",
                    entity_type="task",
                    entity_id=task_id,
                    tenant_id=tenant_id,
                    user_id=mentioned_user_id,
                    metadata=EventMetadata(
                        source="task_comment_service",
                        version="1.0",
                        additional_data={
                            "task_id": str(task_id),
                            "comment_id": comment_id,
                            "mentioned_by": str(user_id),
                        },
                    ),
                )

        logger.info(f"Comment {comment_id} added to task {task_id}")

        return comment

    def update_comment(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        comment_id: str,
        content: str,
    ) -> dict[str, Any] | None:
        """Actualizar comentario.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario
            comment_id: ID del comentario
            content: Nuevo contenido

        Returns:
            Comentario actualizado o None si no existe
        """
        from app.models.task import Task

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        if not task:
            return None

        # Obtener metadata actual
        metadata = task.task_metadata or {}
        comments = metadata.get("comments", [])

        # Buscar y actualizar comentario
        comment_found = None
        for comment in comments:
            if comment.get("id") == comment_id:
                # Verificar que el usuario sea el autor
                if comment.get("user_id") != str(user_id):
                    logger.warning(
                        f"User {user_id} attempted to update comment {comment_id} "
                        f"owned by {comment.get('user_id')}"
                    )
                    return None

                comment["content"] = content
                comment["updated_at"] = datetime.now(UTC).isoformat()
                comment_found = comment
                break

        if not comment_found:
            return None

        metadata["comments"] = comments
        task.task_metadata = metadata
        self.db.commit()

        # Publicar evento
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.comment_updated",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_comment_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                    "comment_id": comment_id,
                },
            ),
        )

        logger.info(f"Comment {comment_id} updated in task {task_id}")

        return comment_found

    def delete_comment(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        comment_id: str,
    ) -> bool:
        """Eliminar comentario.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant
            user_id: ID del usuario
            comment_id: ID del comentario

        Returns:
            True si se eliminó correctamente
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
        comments = metadata.get("comments", [])

        # Buscar comentario
        comment_to_delete = None
        for comment in comments:
            if comment.get("id") == comment_id:
                # Verificar que el usuario sea el autor
                if comment.get("user_id") != str(user_id):
                    logger.warning(
                        f"User {user_id} attempted to delete comment {comment_id} "
                        f"owned by {comment.get('user_id')}"
                    )
                    return False
                comment_to_delete = comment
                break

        if not comment_to_delete:
            return False

        # Eliminar comentario
        comments = [c for c in comments if c.get("id") != comment_id]
        metadata["comments"] = comments
        task.task_metadata = metadata
        self.db.commit()

        # Publicar evento
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
            event_type="task.comment_deleted",
            entity_type="task",
            entity_id=task_id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="task_comment_service",
                version="1.0",
                additional_data={
                    "task_id": str(task_id),
                    "comment_id": comment_id,
                },
            ),
        )

        logger.info(f"Comment {comment_id} deleted from task {task_id}")

        return True

    def list_comments(
        self,
        task_id: UUID,
        tenant_id: UUID,
    ) -> list[dict[str, Any]]:
        """Listar comentarios de una tarea.

        Args:
            task_id: ID de la tarea
            tenant_id: ID del tenant

        Returns:
            Lista de comentarios ordenados por fecha
        """
        from app.models.task import Task

        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        if not task:
            return []

        metadata = task.task_metadata or {}
        comments = metadata.get("comments", [])

        # Ordenar por fecha de creación (más recientes primero)
        return sorted(
            comments,
            key=lambda c: c.get("created_at", ""),
            reverse=True
        )


def get_task_comment_service(db: Session) -> TaskCommentService:
    """Obtener instancia del servicio de comentarios.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskCommentService
    """
    return TaskCommentService(db)
