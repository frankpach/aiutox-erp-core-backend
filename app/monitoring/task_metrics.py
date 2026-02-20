"""Métricas de negocio para el módulo Tasks usando Prometheus."""

from datetime import datetime
from uuid import UUID

try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Fallback para cuando Prometheus no esté disponible
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def observe(self, *args, **kwargs):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def set(self, *args, **kwargs):
            pass


# Métricas de negocio
tasks_created_total = Counter(
    "tasks_created_total",
    "Total de tareas creadas",
    ["tenant_id", "priority", "template_used"],
)

tasks_completed_total = Counter(
    "tasks_completed_total",
    "Total de tareas completadas",
    ["tenant_id", "priority", "days_to_complete"],
)

task_creation_duration = Histogram(
    "task_creation_duration_seconds", "Duración de creación de tareas", ["tenant_id"]
)

active_tasks_total = Gauge(
    "active_tasks_total", "Total de tareas activas", ["tenant_id", "status"]
)

template_usage_total = Counter(
    "template_usage_total", "Uso de templates", ["template_id", "tenant_id"]
)

task_overdue_total = Gauge(
    "task_overdue_total", "Total de tareas vencidas", ["tenant_id"]
)


class TaskMetrics:
    """Colector de métricas de negocio para Tasks."""

    def __init__(self):
        """Inicializa el colector de métricas."""
        self.prometheus_available = PROMETHEUS_AVAILABLE

    def record_task_created(
        self,
        tenant_id: UUID,
        priority: str,
        template_used: bool = False,
        template_id: UUID | None = None,
    ):
        """Registra creación de tarea."""
        if not self.prometheus_available:
            return

        tasks_created_total.labels(
            tenant_id=str(tenant_id),
            priority=priority,
            template_used=str(template_used),
        ).inc()

        if template_used and template_id:
            template_usage_total.labels(
                template_id=str(template_id), tenant_id=str(tenant_id)
            ).inc()

    def record_task_completed(
        self, tenant_id: UUID, priority: str, created_at: datetime
    ):
        """Registra tarea completada."""
        if not self.prometheus_available:
            return

        days_to_complete = (datetime.utcnow() - created_at).days

        tasks_completed_total.labels(
            tenant_id=str(tenant_id),
            priority=priority,
            days_to_complete=str(days_to_complete),
        ).inc()

    def update_active_tasks(self, tenant_id: UUID, status_counts: dict[str, int]):
        """Actualiza contador de tareas activas."""
        if not self.prometheus_available:
            return

        for status, count in status_counts.items():
            active_tasks_total.labels(tenant_id=str(tenant_id), status=status).set(
                count
            )

    def update_overdue_tasks(self, tenant_id: UUID, count: int):
        """Actualiza contador de tareas vencidas."""
        if not self.prometheus_available:
            return

        task_overdue_total.labels(tenant_id=str(tenant_id)).set(count)

    def record_task_creation_duration(self, tenant_id: UUID, duration_seconds: float):
        """Registra duración de creación de tarea."""
        if not self.prometheus_available:
            return

        task_creation_duration.labels(tenant_id=str(tenant_id)).observe(
            duration_seconds
        )


# Singleton
_task_metrics = None


def get_task_metrics() -> TaskMetrics:
    """Obtiene instancia singleton de métricas."""
    global _task_metrics
    if _task_metrics is None:
        _task_metrics = TaskMetrics()
    return _task_metrics
