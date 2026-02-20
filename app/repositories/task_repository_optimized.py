"""Task repository optimizado con eager loading y mejoras de rendimiento."""

from typing import Any
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.task import (
    Task,
    TaskAssignment,
    TaskChecklistItem,
)


class TaskRepositoryOptimized:
    """Repository optimizado para operaciones de datos de tareas."""

    def __init__(self, db: Session):
        """Inicializar repositorio con sesión de base de datos."""
        self.db = db

    # Task operations optimizados
    def create_task(self, task_data: dict) -> Task:
        """Crear una nueva tarea."""
        task = Task(**task_data)
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task_by_id(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Obtener tarea por ID y tenant con eager loading básico."""
        return (
            self.db.query(Task)
            .options(
                joinedload(Task.checklist_items),
                joinedload(Task.assignments),
                joinedload(Task.tags),
            )
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

    def get_task_by_id_full(self, task_id: UUID, tenant_id: UUID) -> Task | None:
        """Obtener tarea por ID y tenant con todas las relaciones cargadas."""
        return (
            self.db.query(Task)
            .options(
                joinedload(Task.checklist_items),
                joinedload(Task.assignments),
                joinedload(Task.tags),
                joinedload(Task.reminders),
                joinedload(Task.comments),
                joinedload(Task.files),
                joinedload(Task.dependencies),
                joinedload(Task.dependents),
                selectinload(Task.workflow_executions),
            )
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

    def get_all_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
        include_relations: bool = False,
    ) -> list[Task]:
        """Obtener todas las tareas de un tenant con filtros optimizados."""
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        # Aplicar eager loading solo si se solicita
        if include_relations:
            query = query.options(
                joinedload(Task.assignments),
                joinedload(Task.tags),
            )

        # Aplicar filtros
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if assigned_to_id:
            query = query.filter(Task.assigned_to_id == assigned_to_id)

        return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_tasks_with_group_visibility_optimized(
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
        """
        Obtener tareas visibles para un usuario considerando asignaciones de grupo.
        Versión optimizada que evita subconsultas N+1.
        """
        # Construir consulta base con eager loading condicional
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        if include_relations:
            query = query.options(
                joinedload(Task.assignments),
                joinedload(Task.tags),
            )

        # Optimización: Usar EXISTS en lugar de subconsultas para mejor rendimiento
        from sqlalchemy import exists

        # Condición para tareas creadas por el usuario
        created_by_condition = Task.created_by_id == user_id

        # Condición para tareas asignadas directamente
        assigned_directly_condition = Task.assigned_to_id == user_id

        # Condición para tareas asignadas al usuario via TaskAssignment
        assigned_via_task_condition = exists().where(
            TaskAssignment.task_id == Task.id,
            TaskAssignment.tenant_id == tenant_id,
            TaskAssignment.assigned_to_id == user_id,
        )

        # Construir condiciones de visibilidad
        visibility_conditions = [
            created_by_condition,
            assigned_directly_condition,
            assigned_via_task_condition,
        ]

        # Si el usuario pertenece a grupos, incluir tareas asignadas a esos grupos
        if user_group_ids:
            assigned_via_group_condition = exists().where(
                TaskAssignment.task_id == Task.id,
                TaskAssignment.tenant_id == tenant_id,
                TaskAssignment.assigned_to_group_id.in_(user_group_ids),
            )
            visibility_conditions.append(assigned_via_group_condition)

        query = query.filter(or_(*visibility_conditions))

        # Aplicar filtros adicionales
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)

        return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_tasks_by_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        include_relations: bool = False,
    ) -> list[Task]:
        """Obtener tareas por entidad relacionada con eager loading opcional."""
        query = self.db.query(Task).filter(
            Task.related_entity_type == entity_type,
            Task.related_entity_id == entity_id,
            Task.tenant_id == tenant_id,
        )

        if include_relations:
            query = query.options(
                joinedload(Task.assignments),
                joinedload(Task.tags),
            )

        return query.order_by(Task.created_at.desc()).all()

    def update_task(
        self, task_id: UUID, tenant_id: UUID, task_data: dict
    ) -> Task | None:
        """Actualizar una tarea."""
        task = self.get_task_by_id(task_id, tenant_id)
        if not task:
            return None
        for key, value in task_data.items():
            setattr(task, key, value)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete_task(self, task_id: UUID, tenant_id: UUID) -> bool:
        """Eliminar una tarea."""
        task = self.get_task_by_id(task_id, tenant_id)
        if not task:
            return False
        self.db.delete(task)
        self.db.commit()
        return True

    # Checklist operations optimizados
    def create_checklist_item(self, item_data: dict) -> TaskChecklistItem:
        """Crear un nuevo ítem de checklist."""
        item = TaskChecklistItem(**item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_checklist_items(
        self, task_id: UUID, tenant_id: UUID
    ) -> list[TaskChecklistItem]:
        """Obtener todos los ítems de checklist de una tarea."""
        return (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.task_id == task_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .order_by(TaskChecklistItem.order)
            .all()
        )

    def get_checklist_items_with_task(
        self, task_id: UUID, tenant_id: UUID
    ) -> Task | None:
        """Obtener tarea con sus ítems de checklist cargados."""
        return (
            self.db.query(Task)
            .options(joinedload(Task.checklist_items))
            .filter(Task.id == task_id, Task.tenant_id == tenant_id)
            .first()
        )

    def update_checklist_item(
        self, item_id: UUID, tenant_id: UUID, item_data: dict
    ) -> TaskChecklistItem | None:
        """Actualizar un ítem de checklist."""
        item = (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.id == item_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .first()
        )
        if not item:
            return None
        for key, value in item_data.items():
            setattr(item, key, value)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_checklist_item(self, item_id: UUID, tenant_id: UUID) -> bool:
        """Eliminar un ítem de checklist."""
        item = (
            self.db.query(TaskChecklistItem)
            .filter(
                TaskChecklistItem.id == item_id,
                TaskChecklistItem.tenant_id == tenant_id,
            )
            .first()
        )
        if not item:
            return False
        self.db.delete(item)
        self.db.commit()
        return True

    # Assignment operations optimizados
    def create_assignment(self, assignment_data: dict) -> TaskAssignment:
        """Crear una nueva asignación de tarea."""
        assignment = TaskAssignment(**assignment_data)
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def get_assignments_by_task(
        self, task_id: UUID, tenant_id: UUID
    ) -> list[TaskAssignment]:
        """Obtener asignaciones de una tarea con eager loading."""
        return (
            self.db.query(TaskAssignment)
            .options(
                joinedload(TaskAssignment.assigned_to_user),
                joinedload(TaskAssignment.assigned_to_group),
            )
            .filter(
                TaskAssignment.task_id == task_id,
                TaskAssignment.tenant_id == tenant_id,
            )
            .all()
        )

    def get_assignments_by_user(
        self, user_id: UUID, tenant_id: UUID, active_only: bool = True
    ) -> list[TaskAssignment]:
        """Obtener asignaciones de un usuario con eager loading de tareas."""
        query = (
            self.db.query(TaskAssignment)
            .options(joinedload(TaskAssignment.task))
            .filter(
                TaskAssignment.assigned_to_id == user_id,
                TaskAssignment.tenant_id == tenant_id,
            )
        )

        if active_only:
            query = query.join(Task).filter(Task.status.in_(["todo", "in_progress"]))

        return query.all()

    def delete_assignment(self, assignment_id: UUID, tenant_id: UUID) -> bool:
        """Eliminar una asignación."""
        assignment = (
            self.db.query(TaskAssignment)
            .filter(
                TaskAssignment.id == assignment_id,
                TaskAssignment.tenant_id == tenant_id,
            )
            .first()
        )
        if not assignment:
            return False
        self.db.delete(assignment)
        self.db.commit()
        return True

    # Métodos de conteo optimizados
    def count_tasks(
        self,
        tenant_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: UUID | None = None,
    ) -> int:
        """Contar tareas con filtros optimizados."""
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if assigned_to_id:
            query = query.filter(Task.assigned_to_id == assigned_to_id)

        return query.count()

    def count_visible_tasks(
        self,
        tenant_id: UUID,
        user_id: UUID,
        user_group_ids: list[UUID],
        status: str | None = None,
        priority: str | None = None,
    ) -> int:
        """Contar tareas visibles para un usuario de forma optimizada."""
        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        # Usar las mismas condiciones optimizadas que get_tasks_with_group_visibility_optimized
        from sqlalchemy import exists

        visibility_conditions = [
            Task.created_by_id == user_id,
            Task.assigned_to_id == user_id,
            exists().where(
                TaskAssignment.task_id == Task.id,
                TaskAssignment.tenant_id == tenant_id,
                TaskAssignment.assigned_to_id == user_id,
            ),
        ]

        if user_group_ids:
            visibility_conditions.append(
                exists().where(
                    TaskAssignment.task_id == Task.id,
                    TaskAssignment.tenant_id == tenant_id,
                    TaskAssignment.assigned_to_group_id.in_(user_group_ids),
                )
            )

        query = query.filter(or_(*visibility_conditions))

        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)

        return query.count()

    # Batch operations optimizadas
    def bulk_update_task_status(
        self, task_ids: list[UUID], tenant_id: UUID, new_status: str
    ) -> int:
        """Actualizar estado de múltiples tareas en batch."""
        result = (
            self.db.query(Task)
            .filter(
                Task.id.in_(task_ids),
                Task.tenant_id == tenant_id,
            )
            .update({"status": new_status}, synchronize_session=False)
        )
        self.db.commit()
        return result

    def bulk_delete_tasks(self, task_ids: list[UUID], tenant_id: UUID) -> int:
        """Eliminar múltiples tareas en batch."""
        result = (
            self.db.query(Task)
            .filter(
                Task.id.in_(task_ids),
                Task.tenant_id == tenant_id,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return result

    # Métodos de búsqueda optimizados
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
        """Buscar tareas con texto completo optimizado."""
        from sqlalchemy import or_

        query = self.db.query(Task).filter(Task.tenant_id == tenant_id)

        # Búsqueda de texto en campos relevantes
        search_filter = or_(
            Task.title.ilike(f"%{query_text}%"),
            Task.description.ilike(f"%{query_text}%"),
        )
        query = query.filter(search_filter)

        # Aplicar filtros adicionales
        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if assigned_to_id:
            query = query.filter(Task.assigned_to_id == assigned_to_id)

        return query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

    def get_task_statistics(self, tenant_id: UUID) -> dict[str, Any]:
        """Obtener estadísticas de tareas de forma optimizada."""
        from sqlalchemy import func

        stats = (
            self.db.query(
                func.count(Task.id).label("total"),
                func.sum(func.case((Task.status == "todo", 1), else_=0)).label("todo"),
                func.sum(func.case((Task.status == "in_progress", 1), else_=0)).label(
                    "in_progress"
                ),
                func.sum(func.case((Task.status == "done", 1), else_=0)).label("done"),
                func.sum(func.case((Task.priority == "high", 1), else_=0)).label(
                    "high_priority"
                ),
                func.sum(func.case((Task.priority == "medium", 1), else_=0)).label(
                    "medium_priority"
                ),
                func.sum(func.case((Task.priority == "low", 1), else_=0)).label(
                    "low_priority"
                ),
            )
            .filter(Task.tenant_id == tenant_id)
            .first()
        )

        return {
            "total": stats.total or 0,
            "by_status": {
                "todo": stats.todo or 0,
                "in_progress": stats.in_progress or 0,
                "done": stats.done or 0,
            },
            "by_priority": {
                "high": stats.high_priority or 0,
                "medium": stats.medium_priority or 0,
                "low": stats.low_priority or 0,
            },
        }
