"""Bug fixes y mejoras de estabilidad para TaskService."""

from datetime import UTC, datetime
from uuid import UUID


def ensure_timezone_aware(dt: datetime | None) -> datetime | None:
    """Asegura que un datetime tenga timezone UTC."""
    if dt is None:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)

    return dt


def validate_task_dates(
    start_at: datetime | None, due_date: datetime | None, end_at: datetime | None
) -> tuple[datetime | None, datetime | None, datetime | None]:
    """
    Valida y normaliza fechas de tareas.

    Reglas:
    - Todas las fechas deben tener timezone UTC
    - start_at debe ser anterior a due_date
    - due_date debe ser anterior a end_at
    - Si solo hay due_date, es válido
    """
    # Asegurar timezone
    start_at = ensure_timezone_aware(start_at)
    due_date = ensure_timezone_aware(due_date)
    end_at = ensure_timezone_aware(end_at)

    # Validar orden de fechas
    if start_at and due_date and start_at > due_date:
        raise ValueError(
            "La fecha de inicio no puede ser posterior a la fecha de vencimiento"
        )

    if due_date and end_at and due_date > end_at:
        raise ValueError(
            "La fecha de vencimiento no puede ser posterior a la fecha de fin"
        )

    if start_at and end_at and start_at > end_at:
        raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")

    return start_at, due_date, end_at


def validate_circular_dependencies(
    db, task_id: UUID, depends_on_id: UUID, max_depth: int = 50
) -> bool:
    """
    Verifica si agregar una dependencia crearía un ciclo.

    Args:
        db: Sesión de base de datos
        task_id: ID de la tarea que depende
        depends_on_id: ID de la tarea de la que depende
        max_depth: Profundidad máxima para prevenir stack overflow

    Returns:
        True si crearía un ciclo, False si es válido

    Raises:
        ValueError: Si se excede la profundidad máxima
    """
    from app.models.task import TaskDependency

    if task_id == depends_on_id:
        return True

    visited = set()

    def has_path(from_id: UUID, to_id: UUID, depth: int = 0) -> bool:
        if depth > max_depth:
            raise ValueError(
                f"Profundidad máxima de dependencias excedida ({max_depth})"
            )

        if from_id == to_id:
            return True

        if from_id in visited:
            return False

        visited.add(from_id)

        dependencies = (
            db.query(TaskDependency)
            .filter(TaskDependency.task_id == from_id)
            .limit(20)
            .all()
        )

        for dep in dependencies:
            if has_path(dep.depends_on_id, to_id, depth + 1):
                return True

        return False

    return has_path(depends_on_id, task_id)


def validate_title_length(title: str, max_length: int = 255) -> None:
    """Valida la longitud del título de una tarea."""
    if not title or not title.strip():
        raise ValueError("El título es obligatorio")

    if len(title) > max_length:
        raise ValueError(f"El título no puede exceder {max_length} caracteres")


def validate_priority(priority: str) -> None:
    """Valida que la prioridad sea válida."""
    valid_priorities = ["low", "medium", "high", "urgent"]

    if priority not in valid_priorities:
        raise ValueError(
            f"Prioridad inválida: {priority}. Debe ser una de: {', '.join(valid_priorities)}"
        )


def validate_status(status: str) -> None:
    """Valida que el estado sea válido."""
    valid_statuses = [
        "todo",
        "in_progress",
        "on_hold",
        "blocked",
        "review",
        "done",
        "cancelled",
    ]

    if status not in valid_statuses:
        raise ValueError(
            f"Estado inválido: {status}. Debe ser uno de: {', '.join(valid_statuses)}"
        )
