"""Service for managing task dependencies."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.task import Task
from app.models.task_dependency import TaskDependency

logger = get_logger(__name__)


class TaskDependencyService:
    """Servicio para gestionar dependencias entre tareas."""

    def __init__(self, db: Session):
        """Initialize dependency service."""
        self.db = db

    def add_dependency(
        self,
        task_id: UUID,
        depends_on_id: UUID,
        tenant_id: UUID,
        dependency_type: str = "finish_to_start"
    ) -> TaskDependency:
        """Agrega dependencia entre tareas."""

        # Validar que no sea la misma tarea
        if task_id == depends_on_id:
            raise ValueError("Una tarea no puede depender de sí misma")

        # Validar que ambas tareas existan y pertenezcan al mismo tenant
        task = self.db.query(Task).filter(
            Task.id == task_id,
            Task.tenant_id == tenant_id
        ).first()

        depends_on_task = self.db.query(Task).filter(
            Task.id == depends_on_id,
            Task.tenant_id == tenant_id
        ).first()

        if not task:
            raise ValueError(f"Tarea {task_id} no encontrada o no pertenece al tenant")

        if not depends_on_task:
            raise ValueError(f"Tarea de dependencia {depends_on_id} no encontrada o no pertenece al tenant")

        # Validar dependencias circulares
        if self._would_create_cycle(task_id, depends_on_id):
            raise ValueError("La dependencia crearía un ciclo")

        # Crear dependencia
        dependency = TaskDependency(
            tenant_id=tenant_id,
            task_id=task_id,
            depends_on_id=depends_on_id,
            dependency_type=dependency_type
        )

        self.db.add(dependency)
        self.db.commit()
        self.db.refresh(dependency)

        logger.info(f"Dependency created: task {task_id} depends on {depends_on_id}")
        return dependency

    def _would_create_cycle(self, task_id: UUID, depends_on_id: UUID) -> bool:
        """Verifica si agregar la dependencia crearía un ciclo."""
        visited = set()
        max_depth = 50  # Prevenir stack overflow

        def has_path(from_id: UUID, to_id: UUID, depth: int = 0) -> bool:
            if depth > max_depth:
                raise ValueError("Profundidad máxima de dependencias excedida")

            if from_id == to_id:
                return True

            if from_id in visited:
                return False

            visited.add(from_id)

            dependencies = self.db.query(TaskDependency).filter(
                TaskDependency.task_id == from_id
            ).limit(20).all()

            for dep in dependencies:
                if has_path(dep.depends_on_id, to_id, depth + 1):
                    return True

            return False

        return has_path(depends_on_id, task_id)

    def get_dependencies(self, task_id: UUID, tenant_id: UUID) -> list[TaskDependency]:
        """Obtiene dependencias de una tarea."""
        return self.db.query(TaskDependency).filter(
            TaskDependency.task_id == task_id,
            TaskDependency.tenant_id == tenant_id
        ).all()

    def get_dependents(self, task_id: UUID, tenant_id: UUID) -> list[TaskDependency]:
        """Obtiene tareas que dependen de esta."""
        return self.db.query(TaskDependency).filter(
            TaskDependency.depends_on_id == task_id,
            TaskDependency.tenant_id == tenant_id
        ).all()

    def remove_dependency(self, dependency_id: UUID, tenant_id: UUID) -> bool:
        """Elimina una dependencia."""
        dependency = self.db.query(TaskDependency).filter(
            TaskDependency.id == dependency_id,
            TaskDependency.tenant_id == tenant_id
        ).first()

        if not dependency:
            return False

        self.db.delete(dependency)
        self.db.commit()

        logger.info(f"Dependency removed: {dependency_id}")
        return True


def get_task_dependency_service(db: Session) -> TaskDependencyService:
    """Get task dependency service instance."""
    return TaskDependencyService(db)
