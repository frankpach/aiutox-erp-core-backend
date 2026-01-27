"""Flow Runs router for workflow execution tracking."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.flow_runs.service import FlowRunService
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.flow_run import (
    FlowRunCreate,
    FlowRunResponse,
    FlowRunStatsResponse,
    FlowRunUpdate,
)

router = APIRouter()


def get_flow_runs_service(
    db: Annotated[Session, Depends(get_db)],
) -> FlowRunService:
    """Dependency to get FlowRunService."""
    return FlowRunService(db)


# Flow Run endpoints
@router.post(
    "",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create flow run",
    description="Create a new flow run. Requires flow_runs.manage permission.",
)
async def create_flow_run(
    flow_run_data: FlowRunCreate,
    current_user: Annotated[User, Depends(require_permission("flow_runs.manage"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
) -> StandardResponse[FlowRunResponse]:
    """Create a new flow run."""
    flow_run = service.create_flow_run(
        flow_id=flow_run_data.flow_id,
        entity_type=flow_run_data.entity_type,
        entity_id=flow_run_data.entity_id,
        tenant_id=current_user.tenant_id,
        run_metadata=flow_run_data.run_metadata,
    )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.get(
    "",
    response_model=StandardListResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List flow runs",
    description="List flow runs. Requires flow_runs.view permission.",
)
async def list_flow_runs(
    current_user: Annotated[User, Depends(require_permission("flow_runs.view"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
    flow_id: UUID | None = Query(None, description="Filter by flow ID"),
    status: str | None = Query(None, description="Filter by status"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[FlowRunResponse]:
    """List flow runs."""
    skip = (page - 1) * page_size
    flow_runs = service.get_flow_runs(
        tenant_id=current_user.tenant_id,
        flow_id=flow_id,
        status=status,
        entity_type=entity_type,
        limit=page_size,
        offset=skip,
    )

    total = len(flow_runs)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[FlowRunResponse.model_validate(fr) for fr in flow_runs],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/stats",
    response_model=StandardResponse[FlowRunStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get flow runs statistics",
    description="Get flow runs statistics. Requires flow_runs.view permission.",
)
async def get_flow_runs_stats(
    current_user: Annotated[User, Depends(require_permission("flow_runs.view"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
) -> StandardResponse[FlowRunStatsResponse]:
    """Get flow runs statistics."""
    stats = service.get_flow_runs_stats(current_user.tenant_id)

    return StandardResponse(
        data=FlowRunStatsResponse(**stats),
    )


@router.get(
    "/by-entity",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Get flow run by entity",
    description="Get flow run by entity type and ID. Requires flow_runs.view permission.",
)
async def get_flow_run_by_entity(
    current_user: Annotated[User, Depends(require_permission("flow_runs.view"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
    entity_type: str = Query(..., description="Entity type"),
    entity_id: UUID = Query(..., description="Entity ID"),
) -> StandardResponse[FlowRunResponse]:
    """Get flow run by entity."""
    flow_run = service.get_flow_run_by_entity(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
    )
    if not flow_run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.get(
    "/{run_id}",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Get flow run",
    description="Get flow run by ID. Requires flow_runs.view permission.",
)
async def get_flow_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(require_permission("flow_runs.view"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
) -> StandardResponse[FlowRunResponse]:
    """Get flow run by ID."""
    flow_run = service.get_flow_run_by_id(run_id, current_user.tenant_id)
    if not flow_run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.put(
    "/{run_id}",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Update flow run",
    description="Update flow run. Requires flow_runs.manage permission.",
)
async def update_flow_run(
    run_id: UUID,
    update_data: FlowRunUpdate,
    current_user: Annotated[User, Depends(require_permission("flow_runs.manage"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
) -> StandardResponse[FlowRunResponse]:
    """Update flow run."""
    flow_run = service.update_flow_run(
        run_id=run_id,
        tenant_id=current_user.tenant_id,
        update_data=update_data.model_dump(exclude_none=True),
    )
    if not flow_run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.post(
    "/{run_id}/start",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Start flow run",
    description="Start a flow run. Requires flow_runs.manage permission.",
)
async def start_flow_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(require_permission("flow_runs.manage"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
) -> StandardResponse[FlowRunResponse]:
    """Start a flow run."""
    flow_run = service.start_flow_run(run_id, current_user.tenant_id)
    if not flow_run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.post(
    "/{run_id}/complete",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Complete flow run",
    description="Complete a flow run. Requires flow_runs.manage permission.",
)
async def complete_flow_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(require_permission("flow_runs.manage"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
    metadata: dict | None = None,
) -> StandardResponse[FlowRunResponse]:
    """Complete a flow run."""
    flow_run = service.complete_flow_run(
        run_id=run_id,
        tenant_id=current_user.tenant_id,
        metadata=metadata,
    )
    if not flow_run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.post(
    "/{run_id}/fail",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Fail flow run",
    description="Fail a flow run. Requires flow_runs.manage permission.",
)
async def fail_flow_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(require_permission("flow_runs.manage"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
    error_message: str | None = None,
    metadata: dict | None = None,
) -> StandardResponse[FlowRunResponse]:
    """Fail a flow run."""
    flow_run = service.fail_flow_run(
        run_id=run_id,
        tenant_id=current_user.tenant_id,
        error_message=error_message,
        metadata=metadata,
    )
    if not flow_run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.post(
    "/{run_id}/cancel",
    response_model=StandardResponse[FlowRunResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel flow run",
    description="Cancel a flow run. Requires flow_runs.manage permission.",
)
async def cancel_flow_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(require_permission("flow_runs.manage"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
) -> StandardResponse[FlowRunResponse]:
    """Cancel a flow run."""
    flow_run = service.cancel_flow_run(run_id, current_user.tenant_id)
    if not flow_run:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )

    return StandardResponse(
        data=FlowRunResponse.model_validate(flow_run),
    )


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete flow run",
    description="Delete a flow run. Requires flow_runs.manage permission.",
)
async def delete_flow_run(
    run_id: UUID,
    current_user: Annotated[User, Depends(require_permission("flow_runs.manage"))],
    service: Annotated[FlowRunService, Depends(get_flow_runs_service)],
):
    """Delete a flow run."""
    deleted = service.delete_flow_run(run_id, current_user.tenant_id)
    if not deleted:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flow run not found",
        )
