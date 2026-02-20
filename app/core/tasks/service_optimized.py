"""Task service optimizado con eager loading y mejoras de rendimiento."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache.task_cache import get_task_cache
from app.core.logging import get_logger
from app.core.pubsub import get_event_publisher
from app.core.pubsub.event_helpers import safe_publish_event
from app.core.pubsub.models import EventMetadata
from app.core.tasks.audit_integration import get_task_audit_service
from app.core.tasks.notification_service import get_task_notification_service
from app.core.tasks.templates import get_task_template_service
from app.core.tasks.webhooks import get_task_webhook_service
from app.models.task import Task, TaskPriority, TaskStatusEnum
from app.repositories.task_repository_optimized import TaskRepositoryOptimized

logger = get_logger(__name__)


class TaskServiceOptimized:
    """Service optimizado para gestión de tareas con eager loading y caché."""

    def __init__(
        self,
        db: Session,
        event_publisher: Any | None = None,
    ) -> None:
        """Inicializar servicio de tareas optimizado."""
        self.db = db
        self.repository = TaskRepositoryOptimized(db)
        self.event_publisher = event_publisher or get_event_publisher()
        self.notification_service = get_task_notification_service(db)
        self.audit_service = get_task_audit_service(db)
        self.webhook_service = get_task_webhook_service(db)
        self.template_service = get_task_template_service(db)
        self.cache = get_task_cache()

    async def create_task(
        self,
        title: str,
        tenant_id: UUID,
        created_by_id: UUID,
        description: str | None = None,
        status: str = TaskStatusEnum.TODO,
        priority: str = TaskPriority.MEDIUM,
        assigned_to_id: UUID | None = None,
        due_date: datetime | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        all_day: bool = False,
        tags: list[str] | None = None,
        tag_ids: list[UUID] | None = None,
        color_override: str | None = None,
        estimated_duration: int | None = None,
        category: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
        source_module: str | None = None,
        source_id: UUID | None = None,
        source_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Crear una nueva tarea con optimizaciones de rendimiento."""
        task = self.repository.create_task(
            {
                "tenant_id": tenant_id,
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
                "assigned_to_id": assigned_to_id,
                "created_by_id": created_by_id,
                "due_date": due_date,
                "start_at": start_at,
                "end_at": end_at,
                "all_day": all_day,
                "color_override": color_override,
                "estimated_duration": estimated_duration,
                "category": category,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "source_module": source_module,
                "source_id": source_id,
                "source_context": source_context,
                "metadata": metadata,
            }
        )

        # Invalidar caché relevante
        self._invalidate_task_cache(tenant_id, created_by_id, assigned_to_id)

        # Publicar evento
        await safe_publish_event(
            self.event_publisher,
            "task.created",
            {
                "task_id": str(task.id),
                "tenant_id": str(tenant_id),
                "created_by_id": str(created_by_id),
                "assigned_to_id": str(assigned_to_id) if assigned_to_id else None,
                "title": title,
                "status": status,
                "priority": priority,
            },
            EventMetadata(
                tenant_id=tenant_id,
                user_id=created_by_id,
                entity_type="task",
                entity_id=task.id,
            ),
        )

        # Enviar notificaciones si aplica
        if assigned_to_id and assigned_to_id != created_by_id:
            await self.notification_service.notify_task_assigned(
                task_id=task.id,
                assigned_to_id=assigned_to_id,
                assigned_by_id=created_by_id,
            )

        return task

    def get_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        include_relations: bool = False,
    ) -> Task | None:
        """Obtener una tarea con eager loading optimizado."""
        # Intentar caché primero
        cache_key = (
            f"task:{task_id}:{tenant_id}:{'full' if include_relations else 'basic'}"
        )
        cached_task = self.cache.get(cache_key)
        if cached_task:
            return cached_task

        # Obtener de base de datos con eager loading apropiado
        if include_relations:
            task = self.repository.get_task_by_id_full(task_id, tenant_id)
        else:
            task = self.repository.get_task_by_id(task_id, tenant_id)

        # Cachear resultado por 5 minutos
        if task:
            self.cache.set(cache_key, task, ttl=300)

        return task

    def get_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
        include_relations: bool = False,
    ) -> list[Task]:
        """Obtener tareas con filtros y eager loading optimizado."""
        # Generar clave de caché para filtros
        cache_key = self._generate_tasks_cache_key(
            tenant_id, status, priority, assigned_to_id, skip, limit, include_relations
        )

        # Intentar caché
        cached_tasks = self.cache.get(cache_key)
        if cached_tasks:
            return cached_tasks

        # Obtener de base de datos
        tasks = self.repository.get_all_tasks(
            tenant_id=tenant_id,
            status=status,
            priority=priority,
            assigned_to_id=assigned_to_id,
            skip=skip,
            limit=limit,
            include_relations=include_relations,
        )

        # Cachear resultado por 2 minutos para listados
        self.cache.set(cache_key, tasks, ttl=120)

        return tasks

    def get_visible_tasks(
        self,
        tenant_id: UUID,
        user_id: UUID,
        user_group_ids: list[UUID],
        status: str | None = None,
        priority: str | None = None,
        skip: int = 0,
        limit: int = 100,
        include_relations: bool = False,
    ) -> list[Task]:
        """Obtener tareas visibles para un usuario con optimización de visibilidad."""
        # Generar clave de caché específica para visibilidad
        cache_key = self._generate_visibility_cache_key(
            tenant_id,
            user_id,
            tuple(user_group_ids),
            status,
            priority,
            skip,
            limit,
            include_relations,
        )

        # Intentar caché
        cached_tasks = self.cache.get(cache_key)
        if cached_tasks:
            return cached_tasks

        # Obtener de base de datos con consulta optimizada
        tasks = self.repository.get_tasks_with_group_visibility_optimized(
            tenant_id=tenant_id,
            user_id=user_id,
            user_group_ids=user_group_ids,
            status=status,
            priority=priority,
            skip=skip,
            limit=limit,
            include_relations=include_relations,
        )

        # Cachear por 1 minuto (menos tiempo por datos específicos de usuario)
        self.cache.set(cache_key, tasks, ttl=60)

        return tasks

    def update_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        update_data: dict[str, Any],
        user_id: UUID,
    ) -> Task | None:
        """Actualizar una tarea con invalidación de caché."""
        # Obtener tarea actual para caché
        old_task = self.get_task(task_id, tenant_id)
        if not old_task:
            return None

        # Actualizar en base de datos
        updated_task = self.repository.update_task(task_id, tenant_id, update_data)
        if not updated_task:
            return None

        # Invalidar caché relevante
        self._invalidate_task_cache(
            tenant_id,
            old_task.created_by_id,
            old_task.assigned_to_id,
            updated_task.assigned_to_id,
        )

        # Publicar evento de actualización
        await safe_publish_event(
            self.event_publisher,
            "task.updated",
            {
                "task_id": str(task_id),
                "tenant_id": str(tenant_id),
                "updated_by_id": str(user_id),
                "changes": update_data,
            },
            EventMetadata(
                tenant_id=tenant_id,
                user_id=user_id,
                entity_type="task",
                entity_id=task_id,
            ),
        )

        return updated_task

    async def delete_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Eliminar una tarea con limpieza de caché."""
        # Obtener tarea antes de eliminar para caché
        task = self.get_task(task_id, tenant_id)
        if not task:
            return False

        # Eliminar de base de datos
        deleted = self.repository.delete_task(task_id, tenant_id)
        if not deleted:
            return False

        # Invalidar caché relevante
        self._invalidate_task_cache(
            tenant_id,
            task.created_by_id,
            task.assigned_to_id,
        )

        # Publicar evento de eliminación
        await safe_publish_event(
            self.event_publisher,
            "task.deleted",
            {
                "task_id": str(task_id),
                "tenant_id": str(tenant_id),
                "deleted_by_id": str(user_id),
                "title": task.title,
            },
            EventMetadata(
                tenant_id=tenant_id,
                user_id=user_id,
                entity_type="task",
                entity_id=task_id,
            ),
        )

        return True

    def get_task_statistics(self, tenant_id: UUID) -> dict[str, Any]:
        """Obtener estadísticas de tareas con caché."""
        cache_key = f"task_stats:{tenant_id}"

        # Intentar caché
        cached_stats = self.cache.get(cache_key)
        if cached_stats:
            return cached_stats

        # Obtener de base de datos
        stats = self.repository.get_task_statistics(tenant_id)

        # Cachear por 10 minutos para estadísticas
        self.cache.set(cache_key, stats, ttl=600)

        return stats

    def search_tasks(
        self,
        tenant_id: UUID,
        query_text: str,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """Buscar tareas con texto completo y caché."""
        cache_key = f"task_search:{tenant_id}:{hash(query_text)}:{status}:{priority}:{assigned_to_id}:{skip}:{limit}"

        # Intentar caché
        cached_results = self.cache.get(cache_key)
        if cached_results:
            return cached_results

        # Buscar en base de datos
        results = self.repository.search_tasks(
            tenant_id=tenant_id,
            query_text=query_text,
            status=status,
            priority=priority,
            assigned_to_id=assigned_to_id,
            skip=skip,
            limit=limit,
        )

        # Cachear por 3 minutos para búsquedas
        self.cache.set(cache_key, results, ttl=180)

        return results

    async def bulk_update_task_status(
        self,
        task_ids: list[UUID],
        tenant_id: UUID,
        new_status: str,
        user_id: UUID,
    ) -> int:
        """Actualizar estado de múltiples tareas en batch."""
        # Actualizar en base de datos
        updated_count = self.repository.bulk_update_task_status(
            task_ids, tenant_id, new_status
        )

        if updated_count > 0:
            # Invalidar caché para todas las tareas afectadas
            for task_id in task_ids:
                cache_keys = [
                    f"task:{task_id}:{tenant_id}:basic",
                    f"task:{task_id}:{tenant_id}:full",
                ]
                for key in cache_keys:
                    self.cache.delete(key)

            # Publicar evento de actualización masiva
            await safe_publish_event(
                self.event_publisher,
                "tasks.bulk_updated",
                {
                    "tenant_id": str(tenant_id),
                    "updated_by_id": str(user_id),
                    "task_ids": [str(tid) for tid in task_ids],
                    "new_status": new_status,
                    "updated_count": updated_count,
                },
                EventMetadata(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    entity_type="task",
                    entity_id=None,  # Bulk operation
                ),
            )

        return updated_count

    # Métodos auxiliares de caché
    def _generate_tasks_cache_key(
        self,
        tenant_id: UUID,
        status: str | None,
        priority: str | None,
        assigned_to_id: UUID | None,
        skip: int,
        limit: int,
        include_relations: bool,
    ) -> str:
        """Genera clave de caché para listados de tareas."""
        parts = [
            "tasks",
            str(tenant_id),
            status or "all",
            priority or "all",
            str(assigned_to_id) if assigned_to_id else "all",
            str(skip),
            str(limit),
            "relations" if include_relations else "basic",
        ]
        return ":".join(parts)

    def _generate_visibility_cache_key(
        self,
        tenant_id: UUID,
        user_id: UUID,
        user_group_ids: tuple,
        status: str | None,
        priority: str | None,
        skip: int,
        limit: int,
        include_relations: bool,
    ) -> str:
        """Genera clave de caché para tareas visibles."""
        # Convertir group_ids a string ordenado para consistencia
        groups_str = (
            ",".join(sorted(str(gid) for gid in user_group_ids))
            if user_group_ids
            else "none"
        )

        parts = [
            "visible_tasks",
            str(tenant_id),
            str(user_id),
            groups_str,
            status or "all",
            priority or "all",
            str(skip),
            str(limit),
            "relations" if include_relations else "basic",
        ]
        return ":".join(parts)

    async def _invalidate_task_cache(
        self,
        tenant_id: UUID,
        *user_ids: UUID | None,
    ) -> None:
        """Invalida caché relacionado con tareas para usuarios específicos."""
        # Invalidar caché de listados generales
        general_keys = [
            f"task_stats:{tenant_id}",
        ]
        for key in general_keys:
            self.cache.delete(key)

        # Invalidar caché específico de usuarios si se proporcionan
        for user_id in user_ids:
            if user_id:
                # Invalidar caché de visibilidad para este usuario
                pattern = f"visible_tasks:{tenant_id}:{user_id}:*"
                self.cache.delete_pattern(pattern)

        # Invalidar caché de búsquedas genéricas
        search_pattern = f"task_search:{tenant_id}:*"
        self.cache.delete_pattern(search_pattern)


# Factory function para compatibilidad
def get_task_service_optimized(
    db: Session, event_publisher: Any | None = None
) -> TaskServiceOptimized:
    """Obtener instancia del servicio de tareas optimizado."""
    return TaskServiceOptimized(db, event_publisher)
