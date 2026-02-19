"""Entidad de dominio Task con lógica de negocio encapsulada."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from app.core.exceptions import BusinessRuleException


class TaskStatus(str, Enum):
    """Estados válidos para una tarea."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Prioridades válidas para una tarea."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    """Tipos de tareas."""
    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    RESEARCH = "research"


class Task:
    """Entidad de dominio Task con reglas de negocio."""

    def __init__(
        self,
        id: UUID,
        tenant_id: UUID,
        title: str,
        created_by_id: UUID,
        description: str | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assigned_to_id: UUID | None = None,
        due_date: datetime | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        all_day: bool = False,
        color_override: str | None = None,
        estimated_duration: int | None = None,
        category: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
        source_module: str | None = None,
        source_id: UUID | None = None,
        source_context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        """Inicializar entidad Task con validaciones."""
        self.id = id
        self.tenant_id = tenant_id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.assigned_to_id = assigned_to_id
        self.created_by_id = created_by_id
        self.due_date = due_date
        self.start_at = start_at
        self.end_at = end_at
        self.all_day = all_day
        self.color_override = color_override
        self.estimated_duration = estimated_duration
        self.category = category
        self.related_entity_type = related_entity_type
        self.related_entity_id = related_entity_id
        self.source_module = source_module
        self.source_id = source_id
        self.source_context = source_context or {}
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

        # Validaciones de negocio
        self._validate_business_rules()

    def _validate_business_rules(self) -> None:
        """Validar reglas de negocio al crear/actualizar tarea."""
        if not self.title or len(self.title.strip()) < 3:
            raise BusinessRuleException("El título debe tener al menos 3 caracteres")

        if len(self.title) > 200:
            raise BusinessRuleException("El título no puede exceder 200 caracteres")

        if self.description and len(self.description) > 2000:
            raise BusinessRuleException("La descripción no puede exceder 2000 caracteres")

        # Validar fechas
        if self.start_at and self.end_at and self.start_at > self.end_at:
            raise BusinessRuleException("La fecha de inicio no puede ser posterior a la fecha de fin")

        if self.due_date and self.start_at and self.due_date < self.start_at:
            raise BusinessRuleException("La fecha de vencimiento no puede ser anterior a la fecha de inicio")

        # Validar duración estimada
        if self.estimated_duration is not None and self.estimated_duration <= 0:
            raise BusinessRuleException("La duración estimada debe ser mayor a 0")

        # Validar formato de color
        if self.color_override and not self._is_valid_color(self.color_override):
            raise BusinessRuleException("El color debe estar en formato hexadecimal (#RRGGBB)")

    def _is_valid_color(self, color: str) -> bool:
        """Validar formato de color hexadecimal."""
        import re
        return bool(re.match(r"^#[0-9A-Fa-f]{6}$", color))

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Verificar si la transición de estado es válida."""
        valid_transitions = {
            TaskStatus.TODO: [TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED],
            TaskStatus.IN_PROGRESS: [TaskStatus.DONE, TaskStatus.TODO, TaskStatus.CANCELLED],
            TaskStatus.DONE: [TaskStatus.IN_PROGRESS, TaskStatus.TODO],
            TaskStatus.CANCELLED: [TaskStatus.TODO],
        }

        return new_status in valid_transitions.get(self.status, [])

    def transition_to(self, new_status: TaskStatus, user_id: UUID) -> None:
        """Transicionar a nuevo estado con validación."""
        if not self.can_transition_to(new_status):
            raise BusinessRuleException(
                f"No se puede transicionar de {self.status} a {new_status}"
            )

        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()

        # Registrar transición en metadata
        if "status_history" not in self.metadata:
            self.metadata["status_history"] = []

        self.metadata["status_history"].append({
            "from": old_status.value,
            "to": new_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": str(user_id),
        })

    def assign_to(self, user_id: UUID, assigned_by: UUID) -> None:
        """Asignar tarea a usuario."""
        if user_id == self.assigned_to_id:
            raise BusinessRuleException("La tarea ya está asignada a este usuario")

        old_assignee = self.assigned_to_id
        self.assigned_to_id = user_id
        self.updated_at = datetime.utcnow()

        # Registrar asignación en metadata
        if "assignment_history" not in self.metadata:
            self.metadata["assignment_history"] = []

        self.metadata["assignment_history"].append({
            "from": str(old_assignee) if old_assignee else None,
            "to": str(user_id),
            "assigned_by": str(assigned_by),
            "timestamp": datetime.utcnow().isoformat(),
        })

    def unassign(self, unassigned_by: UUID) -> None:
        """Desasignar tarea."""
        if not self.assigned_to_id:
            raise BusinessRuleException("La tarea no está asignada")

        old_assignee = self.assigned_to_id
        self.assigned_to_id = None
        self.updated_at = datetime.utcnow()

        # Registrar desasignación en metadata
        if "assignment_history" not in self.metadata:
            self.metadata["assignment_history"] = []

        self.metadata["assignment_history"].append({
            "from": str(old_assignee),
            "to": None,
            "assigned_by": str(unassigned_by),
            "timestamp": datetime.utcnow().isoformat(),
        })

    def is_overdue(self) -> bool:
        """Verificar si la tarea está vencida."""
        if not self.due_date:
            return False

        return self.due_date < datetime.utcnow() and self.status != TaskStatus.DONE

    def is_due_soon(self, hours_ahead: int = 24) -> bool:
        """Verificar si la tarea vence pronto."""
        if not self.due_date or self.status == TaskStatus.DONE:
            return False

        from datetime import timedelta
        threshold = datetime.utcnow() + timedelta(hours=hours_ahead)
        return datetime.utcnow() < self.due_date <= threshold

    def get_priority_score(self) -> int:
        """Obtener score numérico de prioridad para ordenamiento."""
        priority_scores = {
            TaskPriority.LOW: 1,
            TaskPriority.MEDIUM: 2,
            TaskPriority.HIGH: 3,
            TaskPriority.URGENT: 4,
        }
        return priority_scores.get(self.priority, 2)

    def get_status_score(self) -> int:
        """Obtener score numérico de estado para ordenamiento."""
        status_scores = {
            TaskStatus.TODO: 1,
            TaskStatus.IN_PROGRESS: 2,
            TaskStatus.DONE: 3,
            TaskStatus.CANCELLED: 4,
        }
        return status_scores.get(self.status, 1)

    def can_be_edited_by(self, user_id: UUID) -> bool:
        """Verificar si un usuario puede editar la tarea."""
        # El creador siempre puede editar
        if self.created_by_id == user_id:
            return True

        # El asignado puede editar
        if self.assigned_to_id == user_id:
            return True

        # Tareas completadas o canceladas no se pueden editar
        if self.status in [TaskStatus.DONE, TaskStatus.CANCELLED]:
            return False

        return False

    def can_be_deleted_by(self, user_id: UUID) -> bool:
        """Verificar si un usuario puede eliminar la tarea."""
        # Solo el creador puede eliminar
        return self.created_by_id == user_id

    def update_fields(
        self,
        updates: dict[str, Any],
        updated_by: UUID,
    ) -> None:
        """Actualizar campos con validación de negocio."""
        if not self.can_be_edited_by(updated_by):
            raise BusinessRuleException("No tienes permiso para editar esta tarea")

        # Guardar valores originales para auditoría
        original_values = {}

        for field, value in updates.items():
            if hasattr(self, field):
                original_values[field] = getattr(self, field)
                setattr(self, field, value)

        # Validar reglas de negocio después de la actualización
        self._validate_business_rules()

        # Actualizar timestamp
        self.updated_at = datetime.utcnow()

        # Registrar cambios en metadata
        if "change_history" not in self.metadata:
            self.metadata["change_history"] = []

        self.metadata["change_history"].append({
            "changed_by": str(updated_by),
            "timestamp": datetime.utcnow().isoformat(),
            "changes": [
                {
                    "field": field,
                    "old_value": str(original_values[field]) if field in original_values else None,
                    "new_value": str(value) if value is not None else None,
                }
                for field, value in updates.items()
                if field in original_values
            ],
        })

    def add_tag(self, tag_name: str) -> None:
        """Agregar etiqueta a la tarea."""
        if "tags" not in self.metadata:
            self.metadata["tags"] = []

        tags = self.metadata["tags"]
        if tag_name not in tags:
            tags.append(tag_name)
            self.updated_at = datetime.utcnow()

    def remove_tag(self, tag_name: str) -> None:
        """Eliminar etiqueta de la tarea."""
        if "tags" in self.metadata:
            tags = self.metadata["tags"]
            if tag_name in tags:
                tags.remove(tag_name)
                self.updated_at = datetime.utcnow()

    def get_tags(self) -> list[str]:
        """Obtener etiquetas de la tarea."""
        return self.metadata.get("tags", [])

    def set_estimated_time(self, hours: int) -> None:
        """Establecer tiempo estimado en horas."""
        if hours <= 0:
            raise BusinessRuleException("El tiempo estimado debe ser mayor a 0")

        self.estimated_duration = hours * 60  # Convertir a minutos
        self.updated_at = datetime.utcnow()

    def get_estimated_hours(self) -> int | None:
        """Obtener tiempo estimado en horas."""
        if self.estimated_duration is None:
            return None
        return self.estimated_duration // 60

    def mark_as_complete(self, completed_by: UUID) -> None:
        """Marcar tarea como completada."""
        if self.status == TaskStatus.DONE:
            raise BusinessRuleException("La tarea ya está completada")

        self.transition_to(TaskStatus.DONE, completed_by)

        # Registrar fecha de completado
        if "completion_info" not in self.metadata:
            self.metadata["completion_info"] = {}

        self.metadata["completion_info"].update({
            "completed_at": datetime.utcnow().isoformat(),
            "completed_by": str(completed_by),
        })

    def is_completed(self) -> bool:
        """Verificar si la tarea está completada."""
        return self.status == TaskStatus.DONE

    def get_completion_percentage(self) -> float:
        """Obtener porcentaje de completitud (basado en checklist)."""
        # Esta es una implementación básica
        # En una implementación real, se basaría en los ítems del checklist

        if self.status == TaskStatus.DONE:
            return 100.0
        elif self.status == TaskStatus.IN_PROGRESS:
            return 50.0
        else:
            return 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario para serialización."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "assigned_to_id": str(self.assigned_to_id) if self.assigned_to_id else None,
            "created_by_id": str(self.created_by_id),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "start_at": self.start_at.isoformat() if self.start_at else None,
            "end_at": self.end_at.isoformat() if self.end_at else None,
            "all_day": self.all_day,
            "color_override": self.color_override,
            "estimated_duration": self.estimated_duration,
            "category": self.category,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": str(self.related_entity_id) if self.related_entity_id else None,
            "source_module": self.source_module,
            "source_id": str(self.source_id) if self.source_id else None,
            "source_context": self.source_context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Crear instancia desde diccionario."""
        # Convertir strings a enums
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])

        if "priority" in data and isinstance(data["priority"], str):
            data["priority"] = TaskPriority(data["priority"])

        # Convertir strings UUID a objetos UUID
        uuid_fields = ["id", "tenant_id", "created_by_id", "assigned_to_id", "related_entity_id", "source_id"]
        for field in uuid_fields:
            if field in data and data[field] is not None:
                data[field] = UUID(data[field])

        # Convertir fechas
        date_fields = ["due_date", "start_at", "end_at", "created_at", "updated_at"]
        for field in date_fields:
            if field in data and data[field] is not None:
                if isinstance(data[field], str):
                    data[field] = datetime.fromisoformat(data[field])

        return cls(**data)
