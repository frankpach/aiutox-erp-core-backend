"""Interfaces y abstracciones para el dominio de Tasks."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from uuid import UUID

from .task_entity import Task, TaskStatus, TaskPriority

# Type variables para genéricos
T = TypeVar("T")


class ITaskRepository(ABC, Generic[T]):
    """Interfaz para repositorio de tareas."""
    
    @abstractmethod
    async def save(self, task: Task) -> Task:
        """Guardar tarea."""
        pass
    
    @abstractmethod
    async def find_by_id(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Buscar tarea por ID."""
        pass
    
    @abstractmethod
    async def find_by_tenant(
        self,
        tenant_id: UUID,
        filters: dict[str, Any] | None = None,
        pagination: dict[str, Any] | None = None,
    ) -> list[Task]:
        """Buscar tareas por tenant."""
        pass
    
    @abstractmethod
    async def find_visible_to_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        user_group_ids: list[UUID],
        filters: dict[str, Any] | None = None,
        pagination: dict[str, Any] | None = None,
    ) -> list[Task]:
        """Buscar tareas visibles para usuario."""
        pass
    
    @abstractmethod
    async def delete(self, task_id: UUID, tenant_id: UUID) -> bool:
        """Eliminar tarea."""
        pass
    
    @abstractmethod
    async def count_by_tenant(
        self,
        tenant_id: UUID,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Contar tareas por tenant."""
        pass


class ITaskService(ABC):
    """Interfaz para servicio de aplicación de tareas."""
    
    @abstractmethod
    async def create_task(
        self,
        title: str,
        tenant_id: UUID,
        created_by_id: UUID,
        **kwargs: Any,
    ) -> Task:
        """Crear nueva tarea."""
        pass
    
    @abstractmethod
    async def update_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        updates: dict[str, Any],
        updated_by: UUID,
    ) -> Task:
        """Actualizar tarea."""
        pass
    
    @abstractmethod
    async def delete_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID,
    ) -> bool:
        """Eliminar tarea."""
        pass
    
    @abstractmethod
    async def assign_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        assigned_to_id: UUID,
        assigned_by: UUID,
    ) -> Task:
        """Asignar tarea a usuario."""
        pass
    
    @abstractmethod
    async def unassign_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        unassigned_by: UUID,
    ) -> Task:
        """Desasignar tarea."""
        pass
    
    @abstractmethod
    async def transition_status(
        self,
        task_id: UUID,
        tenant_id: UUID,
        new_status: TaskStatus,
        user_id: UUID,
    ) -> Task:
        """Transicionar estado de tarea."""
        pass


class ITaskNotificationService(ABC):
    """Interfaz para servicio de notificaciones de tareas."""
    
    @abstractmethod
    async def notify_task_created(
        self,
        task: Task,
        recipients: list[UUID] | None = None,
    ) -> None:
        """Notificar creación de tarea."""
        pass
    
    @abstractmethod
    async def notify_task_assigned(
        self,
        task: Task,
        assigned_to: UUID,
        assigned_by: UUID,
    ) -> None:
        """Notificar asignación de tarea."""
        pass
    
    @abstractmethod
    async def notify_task_status_changed(
        self,
        task: Task,
        old_status: TaskStatus,
        changed_by: UUID,
    ) -> None:
        """Notificar cambio de estado."""
        pass
    
    @abstractmethod
    async def notify_task_due_soon(
        self,
        task: Task,
        hours_ahead: int = 24,
    ) -> None:
        """Notificar tarea próxima a vencer."""
        pass


class ITaskValidationService(ABC):
    """Interfaz para servicio de validación de tareas."""
    
    @abstractmethod
    async def validate_task_creation(
        self,
        task_data: dict[str, Any],
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Validar datos para creación de tarea."""
        pass
    
    @abstractmethod
    async def validate_task_update(
        self,
        task_id: UUID,
        updates: dict[str, Any],
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Validar datos para actualización de tarea."""
        pass
    
    @abstractmethod
    async def validate_task_deletion(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Validar eliminación de tarea."""
        pass


class ITaskSearchService(ABC):
    """Interfaz para servicio de búsqueda de tareas."""
    
    @abstractmethod
    async def search_tasks(
        self,
        tenant_id: UUID,
        query: str,
        filters: dict[str, Any] | None = None,
        pagination: dict[str, Any] | None = None,
    ) -> list[Task]:
        """Buscar tareas por texto."""
        pass
    
    @abstractmethod
    async def get_search_suggestions(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 10,
    ) -> list[str]:
        """Obtener sugerencias de búsqueda."""
        pass


class ITaskAnalyticsService(ABC):
    """Interfaz para servicio de analíticas de tareas."""
    
    @abstractmethod
    async def get_task_statistics(
        self,
        tenant_id: UUID,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Obtener estadísticas de tareas."""
        pass
    
    @abstractmethod
    async def get_completion_metrics(
        self,
        tenant_id: UUID,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Obtener métricas de completitud."""
        pass
    
    @abstractmethod
    async def get_productivity_metrics(
        self,
        tenant_id: UUID,
        user_id: UUID | None = None,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Obtener métricas de productividad."""
        pass


class ITaskWorkflowService(ABC):
    """Interfaz para servicio de workflows de tareas."""
    
    @abstractmethod
    async def create_workflow(
        self,
        tenant_id: UUID,
        workflow_data: dict[str, Any],
        created_by: UUID,
    ) -> dict[str, Any]:
        """Crear workflow."""
        pass
    
    @abstractmethod
    async def execute_workflow_step(
        self,
        workflow_id: UUID,
        step_data: dict[str, Any],
        executed_by: UUID,
    ) -> dict[str, Any]:
        """Ejecutar paso de workflow."""
        pass
    
    @abstractmethod
    async def get_workflow_status(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Obtener estado de workflow."""
        pass


class ITaskIntegrationService(ABC):
    """Interfaz para servicio de integraciones de tareas."""
    
    @abstractmethod
    async def sync_with_external_system(
        self,
        task_id: UUID,
        tenant_id: UUID,
        system_type: str,
        sync_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Sincronizar tarea con sistema externo."""
        pass
    
    @abstractmethod
    async def handle_external_update(
        self,
        task_id: UUID,
        tenant_id: UUID,
        external_data: dict[str, Any],
        source_system: str,
    ) -> Task:
        """Manejar actualización desde sistema externo."""
        pass


class ITaskPermissionService(ABC):
    """Interfaz para servicio de permisos de tareas."""
    
    @abstractmethod
    async def can_create_task(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Verificar si usuario puede crear tareas."""
        pass
    
    @abstractmethod
    async def can_view_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Verificar si usuario puede ver tarea."""
        pass
    
    @abstractmethod
    async def can_edit_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Verificar si usuario puede editar tarea."""
        pass
    
    @abstractmethod
    async def can_delete_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Verificar si usuario puede eliminar tarea."""
        pass
    
    @abstractmethod
    async def can_assign_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        target_user_id: UUID,
    ) -> bool:
        """Verificar si usuario puede asignar tarea."""
        pass


class ITaskCacheService(ABC):
    """Interfaz para servicio de caché de tareas."""
    
    @abstractmethod
    async def get_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
    ) -> Task | None:
        """Obtener tarea del caché."""
        pass
    
    @abstractmethod
    async def set_task(
        self,
        task: Task,
        ttl: int = 300,
    ) -> None:
        """Guardar tarea en caché."""
        pass
    
    @abstractmethod
    async def invalidate_task(
        self,
        task_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Invalidar caché de tarea."""
        pass
    
    @abstractmethod
    async def get_task_list(
        self,
        cache_key: str,
    ) -> list[Task] | None:
        """Obtener listado de tareas del caché."""
        pass
    
    @abstractmethod
    async def set_task_list(
        self,
        cache_key: str,
        tasks: list[Task],
        ttl: int = 120,
    ) -> None:
        """Guardar listado de tareas en caché."""
        pass
    
    @abstractmethod
    async def invalidate_tenant_cache(
        self,
        tenant_id: UUID,
    ) -> None:
        """Invalidar caché de tenant."""
        pass


class ITaskEventPublisher(ABC):
    """Interfaz para publicador de eventos de tareas."""
    
    @abstractmethod
    async def publish_task_created(
        self,
        task: Task,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publicar evento de creación de tarea."""
        pass
    
    @abstractmethod
    async def publish_task_updated(
        self,
        task: Task,
        old_values: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publicar evento de actualización de tarea."""
        pass
    
    @abstractmethod
    async def publish_task_deleted(
        self,
        task_id: UUID,
        tenant_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publicar evento de eliminación de tarea."""
        pass
    
    @abstractmethod
    async def publish_task_assigned(
        self,
        task: Task,
        assigned_to: UUID,
        assigned_by: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publicar evento de asignación de tarea."""
        pass
    
    @abstractmethod
    async def publish_task_status_changed(
        self,
        task: Task,
        old_status: TaskStatus,
        new_status: TaskStatus,
        changed_by: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Publicar evento de cambio de estado."""
        pass


# Value Objects
class TaskFilters:
    """Value object para filtros de tareas."""
    
    def __init__(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assigned_to: UUID | None = None,
        created_by: UUID | None = None,
        category: str | None = None,
        due_date_range: tuple[datetime, datetime] | None = None,
        tags: list[str] | None = None,
    ):
        self.status = status
        self.priority = priority
        self.assigned_to = assigned_to
        self.created_by = created_by
        self.category = category
        self.due_date_range = due_date_range
        self.tags = tags or []
    
    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario."""
        result = {}
        
        if self.status:
            result["status"] = self.status.value
        if self.priority:
            result["priority"] = self.priority.value
        if self.assigned_to:
            result["assigned_to_id"] = str(self.assigned_to)
        if self.created_by:
            result["created_by_id"] = str(self.created_by)
        if self.category:
            result["category"] = self.category
        if self.due_date_range:
            result["due_date_from"] = self.due_date_range[0].isoformat()
            result["due_date_to"] = self.due_date_range[1].isoformat()
        if self.tags:
            result["tags"] = self.tags
        
        return result


class TaskSortOptions:
    """Value object para opciones de ordenamiento."""
    
    def __init__(
        self,
        field: str = "created_at",
        order: str = "desc",
    ):
        self.field = field
        self.order = order.lower()
    
    def is_valid(self) -> bool:
        """Verificar si las opciones son válidas."""
        valid_fields = [
            "created_at",
            "updated_at",
            "title",
            "status",
            "priority",
            "due_date",
            "start_at",
            "end_at",
        ]
        valid_orders = ["asc", "desc"]
        
        return self.field in valid_fields and self.order in valid_orders


class TaskPaginationOptions:
    """Value object para opciones de paginación."""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)
    
    @property
    def offset(self) -> int:
        """Calcular offset para base de datos."""
        return (self.page - 1) * self.page_size
    
    def to_dict(self) -> dict[str, int]:
        """Convertir a diccionario."""
        return {
            "page": self.page,
            "page_size": self.page_size,
            "offset": self.offset,
        }


# Domain Events
class TaskDomainEvent(ABC):
    """Clase base para eventos de dominio de tareas."""
    
    def __init__(
        self,
        task_id: UUID,
        tenant_id: UUID,
        occurred_at: datetime,
        user_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.task_id = task_id
        self.tenant_id = tenant_id
        self.occurred_at = occurred_at
        self.user_id = user_id
        self.metadata = metadata or {}


class TaskCreatedEvent(TaskDomainEvent):
    """Evento de creación de tarea."""
    
    def __init__(
        self,
        task_id: UUID,
        tenant_id: UUID,
        title: str,
        created_by: UUID,
        occurred_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(task_id, tenant_id, occurred_at, created_by, metadata)
        self.title = title


class TaskUpdatedEvent(TaskDomainEvent):
    """Evento de actualización de tarea."""
    
    def __init__(
        self,
        task_id: UUID,
        tenant_id: UUID,
        changes: dict[str, Any],
        updated_by: UUID,
        occurred_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(task_id, tenant_id, occurred_at, updated_by, metadata)
        self.changes = changes


class TaskAssignedEvent(TaskDomainEvent):
    """Evento de asignación de tarea."""
    
    def __init__(
        self,
        task_id: UUID,
        tenant_id: UUID,
        assigned_to: UUID,
        assigned_by: UUID,
        occurred_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(task_id, tenant_id, occurred_at, assigned_by, metadata)
        self.assigned_to = assigned_to


class TaskStatusChangedEvent(TaskDomainEvent):
    """Evento de cambio de estado de tarea."""
    
    def __init__(
        self,
        task_id: UUID,
        tenant_id: UUID,
        old_status: TaskStatus,
        new_status: TaskStatus,
        changed_by: UUID,
        occurred_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(task_id, tenant_id, occurred_at, changed_by, metadata)
        self.old_status = old_status
        self.new_status = new_status


class TaskDeletedEvent(TaskDomainEvent):
    """Evento de eliminación de tarea."""
    
    def __init__(
        self,
        task_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID,
        occurred_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(task_id, tenant_id, occurred_at, deleted_by, metadata)
