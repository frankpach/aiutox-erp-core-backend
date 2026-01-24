"""Task Tag Service for advanced tagging and search.

Sprint 5 - Fase 2: Tags Avanzados
"""

from typing import Any
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskTagService:
    """Servicio para gestión avanzada de tags y búsqueda."""

    def __init__(self, db: Session):
        """Inicializar servicio de tags.

        Args:
            db: Sesión de base de datos
        """
        self.db = db

    def search_tasks(
        self,
        tenant_id: UUID,
        query: str,
        tag_ids: list[UUID] | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 50,
    ) -> list[Any]:
        """Búsqueda avanzada de tareas con full-text.

        Args:
            tenant_id: ID del tenant
            query: Texto de búsqueda
            tag_ids: Filtrar por tags
            status: Filtrar por estado
            priority: Filtrar por prioridad
            limit: Límite de resultados

        Returns:
            Lista de tareas que coinciden
        """
        from app.models.task import Task

        # Query base
        q = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        # Búsqueda full-text en título y descripción
        if query:
            search_pattern = f"%{query}%"
            q = q.filter(
                or_(
                    Task.title.ilike(search_pattern),
                    Task.description.ilike(search_pattern),
                )
            )

        # Filtrar por tags
        if tag_ids:
            # Convertir UUIDs a strings para comparar con JSONB
            tag_ids_str = [str(tag_id) for tag_id in tag_ids]
            for tag_id in tag_ids_str:
                q = q.filter(Task.tag_ids.contains([tag_id]))

        # Filtrar por estado
        if status:
            q = q.filter(Task.status == status)

        # Filtrar por prioridad
        if priority:
            q = q.filter(Task.priority == priority)

        # Ordenar por relevancia (más recientes primero)
        q = q.order_by(Task.created_at.desc())

        # Limitar resultados
        tasks = q.limit(limit).all()

        logger.info(
            f"Search completed: query='{query}', found {len(tasks)} tasks"
        )

        return tasks

    def get_popular_tags(
        self,
        tenant_id: UUID,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Obtener tags más populares.

        Args:
            tenant_id: ID del tenant
            limit: Límite de resultados

        Returns:
            Lista de tags con conteo de uso
        """
        from app.models.task import Task

        # Obtener todas las tareas del tenant
        tasks = self.db.query(Task).filter(
            Task.tenant_id == tenant_id
        ).all()

        # Contar uso de tags
        tag_counts: dict[str, int] = {}

        for task in tasks:
            if task.tag_ids:
                for tag_id in task.tag_ids:
                    tag_counts[tag_id] = tag_counts.get(tag_id, 0) + 1

        # Ordenar por uso
        sorted_tags = sorted(
            tag_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        # Formatear resultado
        result = [
            {"tag_id": tag_id, "count": count}
            for tag_id, count in sorted_tags
        ]

        logger.info(f"Retrieved {len(result)} popular tags for tenant {tenant_id}")

        return result

    def suggest_tags(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 10,
    ) -> list[str]:
        """Sugerir tags basados en búsqueda.

        Args:
            tenant_id: ID del tenant
            query: Texto de búsqueda
            limit: Límite de sugerencias

        Returns:
            Lista de tag IDs sugeridos
        """
        from app.models.task import Task

        # Buscar tareas que coincidan con el query
        search_pattern = f"%{query}%"
        tasks = self.db.query(Task).filter(
            Task.tenant_id == tenant_id,
            or_(
                Task.title.ilike(search_pattern),
                Task.description.ilike(search_pattern),
            )
        ).limit(100).all()

        # Contar tags en tareas encontradas
        tag_counts: dict[str, int] = {}

        for task in tasks:
            if task.tag_ids:
                for tag_id in task.tag_ids:
                    tag_counts[tag_id] = tag_counts.get(tag_id, 0) + 1

        # Ordenar y limitar
        sorted_tags = sorted(
            tag_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        suggestions = [tag_id for tag_id, _ in sorted_tags]

        logger.info(
            f"Generated {len(suggestions)} tag suggestions for query '{query}'"
        )

        return suggestions


def get_task_tag_service(db: Session) -> TaskTagService:
    """Obtener instancia del servicio de tags.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskTagService
    """
    return TaskTagService(db)
