"""Task dependencies API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.api_response import StandardResponse
from app.core.tasks.dependency_service import get_task_dependency_service
from app.models.user import User

router = APIRouter(prefix="/tasks/{task_id}/dependencies", tags=["task-dependencies"])


@router.post(
    "",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Agregar dependencia a tarea"
)
async def add_task_dependency(
    task_id: Annotated[UUID, Path(...)],
    depends_on_id: UUID,
    dependency_type: str = "finish_to_start",
    current_user: Annotated[User, Depends(require_permission("tasks.edit"))] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """Agrega una dependencia a una tarea."""
    dependency_service = get_task_dependency_service(db)

    try:
        dependency = dependency_service.add_dependency(
            task_id=task_id,
            depends_on_id=depends_on_id,
            tenant_id=current_user.tenant_id,
            dependency_type=dependency_type
        )

        return StandardResponse(
            data={
                "id": str(dependency.id),
                "task_id": str(dependency.task_id),
                "depends_on_id": str(dependency.depends_on_id),
                "dependency_type": dependency.dependency_type,
                "created_at": dependency.created_at.isoformat(),
            },
            message="Dependencia agregada correctamente"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=StandardResponse[dict],
    summary="Obtener dependencias de tarea"
)
async def get_task_dependencies(
    task_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("tasks.view"))] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """Obtiene las dependencias de una tarea."""
    dependency_service = get_task_dependency_service(db)

    dependencies = dependency_service.get_dependencies(task_id, current_user.tenant_id)
    dependents = dependency_service.get_dependents(task_id, current_user.tenant_id)

    return StandardResponse(
        data={
            "dependencies": [
                {
                    "id": str(dep.id),
                    "depends_on_id": str(dep.depends_on_id),
                    "dependency_type": dep.dependency_type,
                    "created_at": dep.created_at.isoformat(),
                }
                for dep in dependencies
            ],
            "dependents": [
                {
                    "id": str(dep.id),
                    "task_id": str(dep.task_id),
                    "dependency_type": dep.dependency_type,
                    "created_at": dep.created_at.isoformat(),
                }
                for dep in dependents
            ]
        }
    )


@router.delete(
    "/{dependency_id}",
    response_model=StandardResponse[dict],
    summary="Eliminar dependencia"
)
async def remove_task_dependency(
    task_id: Annotated[UUID, Path(...)],
    dependency_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("tasks.edit"))] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """Elimina una dependencia de tarea."""
    dependency_service = get_task_dependency_service(db)

    success = dependency_service.remove_dependency(dependency_id, current_user.tenant_id)

    if not success:
        raise HTTPException(status_code=404, detail="Dependencia no encontrada")

    return StandardResponse(
        data={"deleted": True},
        message="Dependencia eliminada correctamente"
    )
