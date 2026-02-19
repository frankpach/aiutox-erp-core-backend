"""Task Adoption Analytics.

Sprint 5 - Fase 2: Evaluación y Métricas
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskAdoptionAnalytics:
    """Analiza adopción de features de Tasks."""

    def __init__(self, db: Session):
        """Inicializar analytics.

        Args:
            db: Sesión de base de datos
        """
        self.db = db

    def get_feature_adoption(self, tenant_id: UUID) -> dict[str, Any]:
        """Obtiene métricas de adopción de features.

        Args:
            tenant_id: ID del tenant

        Returns:
            Diccionario con métricas de adopción
        """
        from app.models.task import Task

        # Total de usuarios activos (con tareas)
        total_users_with_tasks = (
            self.db.query(func.count(distinct(Task.created_by_id)))
            .filter(Task.tenant_id == tenant_id)
            .scalar()
            or 0
        )

        # Calendar Sync Adoption
        calendar_adoption = self._calculate_calendar_adoption(
            tenant_id, total_users_with_tasks
        )

        # Files Adoption
        files_adoption = self._calculate_files_adoption(
            tenant_id, total_users_with_tasks
        )

        # Comments Adoption
        comments_adoption = self._calculate_comments_adoption(
            tenant_id, total_users_with_tasks
        )

        # Custom States Adoption
        states_adoption = self._calculate_states_adoption(tenant_id)

        # Search Usage
        search_usage = self._calculate_search_usage(tenant_id)

        return {
            "tenant_id": str(tenant_id),
            "total_users_with_tasks": total_users_with_tasks,
            "calendar_sync_adoption": calendar_adoption,
            "files_adoption": files_adoption,
            "comments_adoption": comments_adoption,
            "custom_states_adoption": states_adoption,
            "search_usage": search_usage,
            "generated_at": datetime.now(UTC).isoformat(),
        }

    def _calculate_calendar_adoption(
        self, tenant_id: UUID, total_users: int
    ) -> dict[str, Any]:
        """Calcula adopción de Calendar Sync."""
        from app.models.task import Task

        # Usuarios con tareas con fechas
        users_with_dates = (
            self.db.query(func.count(distinct(Task.created_by_id)))
            .filter(
                Task.tenant_id == tenant_id,
                (Task.start_at.isnot(None))
                | (Task.due_date.isnot(None))
                | (Task.end_at.isnot(None)),
            )
            .scalar()
            or 0
        )

        # Tareas sincronizadas (con metadata de sync)
        tasks_synced = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.tenant_id == tenant_id,
                Task.task_metadata["calendar_synced"].astext == "true",
            )
            .scalar()
            or 0
        )

        # Usuarios que usan sync
        users_with_sync = (
            self.db.query(func.count(distinct(Task.created_by_id)))
            .filter(
                Task.tenant_id == tenant_id,
                Task.task_metadata["calendar_synced"].astext == "true",
            )
            .scalar()
            or 0
        )

        adoption_rate = (
            (users_with_sync / users_with_dates * 100) if users_with_dates > 0 else 0
        )

        return {
            "users_with_dates": users_with_dates,
            "users_with_sync": users_with_sync,
            "tasks_synced": tasks_synced,
            "adoption_rate_percent": round(adoption_rate, 2),
            "status": self._get_adoption_status(adoption_rate),
        }

    def _calculate_files_adoption(
        self, tenant_id: UUID, total_users: int
    ) -> dict[str, Any]:
        """Calcula adopción de Files."""
        from app.models.task import Task

        # Tareas con archivos adjuntos
        tasks_with_files = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.tenant_id == tenant_id,
                Task.task_metadata["attached_files"].isnot(None),
            )
            .scalar()
            or 0
        )

        # Usuarios que adjuntan archivos
        users_with_files = (
            self.db.query(func.count(distinct(Task.created_by_id)))
            .filter(
                Task.tenant_id == tenant_id,
                Task.task_metadata["attached_files"].isnot(None),
            )
            .scalar()
            or 0
        )

        adoption_rate = (
            (users_with_files / total_users * 100) if total_users > 0 else 0
        )

        return {
            "users_with_files": users_with_files,
            "tasks_with_files": tasks_with_files,
            "adoption_rate_percent": round(adoption_rate, 2),
            "status": self._get_adoption_status(adoption_rate),
        }

    def _calculate_comments_adoption(
        self, tenant_id: UUID, total_users: int
    ) -> dict[str, Any]:
        """Calcula adopción de Comments."""
        from app.models.task import Task

        # Tareas con comentarios
        tasks_with_comments = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.tenant_id == tenant_id,
                Task.task_metadata["comments"].isnot(None),
            )
            .scalar()
            or 0
        )

        # Usuarios que comentan
        users_with_comments = (
            self.db.query(func.count(distinct(Task.created_by_id)))
            .filter(
                Task.tenant_id == tenant_id,
                Task.task_metadata["comments"].isnot(None),
            )
            .scalar()
            or 0
        )

        adoption_rate = (
            (users_with_comments / total_users * 100) if total_users > 0 else 0
        )

        return {
            "users_with_comments": users_with_comments,
            "tasks_with_comments": tasks_with_comments,
            "adoption_rate_percent": round(adoption_rate, 2),
            "status": self._get_adoption_status(adoption_rate),
        }

    def _calculate_states_adoption(self, tenant_id: UUID) -> dict[str, Any]:
        """Calcula adopción de Estados Customizables."""
        from app.models.task_status import TaskStatus

        # Total de estados
        total_states = (
            self.db.query(func.count(TaskStatus.id))
            .filter(TaskStatus.tenant_id == tenant_id)
            .scalar()
            or 0
        )

        # Estados custom (no sistema)
        custom_states = (
            self.db.query(func.count(TaskStatus.id))
            .filter(TaskStatus.tenant_id == tenant_id, not TaskStatus.is_system)
            .scalar()
            or 0
        )

        return {
            "total_states": total_states,
            "custom_states": custom_states,
            "has_custom_states": custom_states > 0,
            "status": "active" if custom_states > 0 else "not_used",
        }

    def _calculate_search_usage(self, tenant_id: UUID) -> dict[str, Any]:
        """Calcula uso de búsqueda (simulado - en producción usar logs)."""
        # En producción, esto vendría de logs de búsqueda
        # Por ahora retornamos estructura esperada
        return {
            "total_searches": 0,
            "avg_searches_per_user": 0,
            "status": "not_measured",
        }

    def _get_adoption_status(self, adoption_rate: float) -> str:
        """Determina estado de adopción basado en tasa.

        Args:
            adoption_rate: Tasa de adopción en porcentaje

        Returns:
            Estado: high, medium, low, not_used
        """
        if adoption_rate >= 40:
            return "high"
        elif adoption_rate >= 20:
            return "medium"
        elif adoption_rate > 0:
            return "low"
        else:
            return "not_used"

    def get_adoption_trends(
        self, tenant_id: UUID, days: int = 30
    ) -> dict[str, Any]:
        """Obtiene tendencias de adopción en el tiempo.

        Args:
            tenant_id: ID del tenant
            days: Días hacia atrás para analizar

        Returns:
            Tendencias de adopción
        """
        from app.models.task import Task

        start_date = datetime.now(UTC) - timedelta(days=days)

        # Tareas creadas en el período
        tasks_in_period = (
            self.db.query(func.count(Task.id))
            .filter(Task.tenant_id == tenant_id, Task.created_at >= start_date)
            .scalar()
            or 0
        )

        # Tareas con sync en el período
        synced_in_period = (
            self.db.query(func.count(Task.id))
            .filter(
                Task.tenant_id == tenant_id,
                Task.created_at >= start_date,
                Task.task_metadata["calendar_synced"].astext == "true",
            )
            .scalar()
            or 0
        )

        return {
            "period_days": days,
            "tasks_created": tasks_in_period,
            "tasks_synced": synced_in_period,
            "sync_rate_percent": round(
                (synced_in_period / tasks_in_period * 100) if tasks_in_period > 0 else 0,
                2,
            ),
        }


def get_task_adoption_analytics(db: Session) -> TaskAdoptionAnalytics:
    """Obtener instancia de analytics.

    Args:
        db: Sesión de base de datos

    Returns:
        Instancia de TaskAdoptionAnalytics
    """
    return TaskAdoptionAnalytics(db)
