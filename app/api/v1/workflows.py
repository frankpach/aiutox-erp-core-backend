"""Workflows router for workflow management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.workflow_service import WorkflowService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.task import (
    WorkflowCreate,
    WorkflowExecutionCreate,
    WorkflowExecutionResponse,
    WorkflowResponse,
    WorkflowStepCreate,
    WorkflowStepResponse,
    WorkflowUpdate,
)

router = APIRouter()


def get_workflow_service(db: Annotated[Session, Depends(get_db)]) -> WorkflowService:
    """Dependency to get WorkflowService."""
    return WorkflowService(db)


@router.post(
    "",
    response_model=StandardResponse[WorkflowResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow",
    description="Create a new workflow. Requires workflows.manage permission.",
)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: Annotated[User, Depends(require_permission("workflows.manage"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> StandardResponse[WorkflowResponse]:
    """Create a new workflow."""
    workflow = service.create_workflow(
        name=workflow_data.name,
        tenant_id=current_user.tenant_id,
        description=workflow_data.description,
        definition=workflow_data.definition,
        enabled=workflow_data.enabled,
        metadata=workflow_data.metadata,
    )

    return StandardResponse(
        data=WorkflowResponse.model_validate(workflow),
        message="Workflow created successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[WorkflowResponse],
    status_code=status.HTTP_200_OK,
    summary="List workflows",
    description="List workflows. Requires workflows.view permission.",
)
async def list_workflows(
    current_user: Annotated[User, Depends(require_permission("workflows.view"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    enabled_only: bool = Query(default=False, description="Only return enabled workflows"),
) -> StandardListResponse[WorkflowResponse]:
    """List workflows."""
    skip = (page - 1) * page_size
    workflows = service.get_workflows(
        tenant_id=current_user.tenant_id,
        enabled_only=enabled_only,
        skip=skip,
        limit=page_size,
    )
    total = len(workflows)  # TODO: Add count method to repository

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[WorkflowResponse.model_validate(w) for w in workflows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Workflows retrieved successfully",
    )


@router.get(
    "/{workflow_id}",
    response_model=StandardResponse[WorkflowResponse],
    status_code=status.HTTP_200_OK,
    summary="Get workflow",
    description="Get a specific workflow by ID. Requires workflows.view permission.",
)
async def get_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    current_user: Annotated[User, Depends(require_permission("workflows.view"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> StandardResponse[WorkflowResponse]:
    """Get a specific workflow."""
    workflow = service.get_workflow(workflow_id, current_user.tenant_id)
    if not workflow:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WORKFLOW_NOT_FOUND",
            message=f"Workflow with ID {workflow_id} not found",
        )

    return StandardResponse(
        data=WorkflowResponse.model_validate(workflow),
        message="Workflow retrieved successfully",
    )


@router.put(
    "/{workflow_id}",
    response_model=StandardResponse[WorkflowResponse],
    status_code=status.HTTP_200_OK,
    summary="Update workflow",
    description="Update a workflow. Requires workflows.manage permission.",
)
async def update_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    workflow_data: WorkflowUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("workflows.manage"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> StandardResponse[WorkflowResponse]:
    """Update a workflow."""
    update_dict = workflow_data.model_dump(exclude_unset=True)
    workflow = service.update_workflow(workflow_id, current_user.tenant_id, update_dict)

    if not workflow:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WORKFLOW_NOT_FOUND",
            message=f"Workflow with ID {workflow_id} not found",
        )

    return StandardResponse(
        data=WorkflowResponse.model_validate(workflow),
        message="Workflow updated successfully",
    )


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workflow",
    description="Delete a workflow. Requires workflows.manage permission.",
)
async def delete_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    current_user: Annotated[User, Depends(require_permission("workflows.manage"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> None:
    """Delete a workflow."""
    deleted = service.delete_workflow(workflow_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WORKFLOW_NOT_FOUND",
            message=f"Workflow with ID {workflow_id} not found",
        )


@router.post(
    "/{workflow_id}/steps",
    response_model=StandardResponse[WorkflowStepResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow step",
    description="Create a workflow step. Requires workflows.manage permission.",
)
async def create_workflow_step(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    step_data: WorkflowStepCreate = ...,
    current_user: Annotated[User, Depends(require_permission("workflows.manage"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> StandardResponse[WorkflowStepResponse]:
    """Create a workflow step."""
    # Verify workflow exists
    workflow = service.get_workflow(workflow_id, current_user.tenant_id)
    if not workflow:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="WORKFLOW_NOT_FOUND",
            message=f"Workflow with ID {workflow_id} not found",
        )

    step = service.create_workflow_step(
        workflow_id=workflow_id,
        tenant_id=current_user.tenant_id,
        name=step_data.name,
        step_type=step_data.step_type,
        order=step_data.order,
        config=step_data.config,
        transitions=step_data.transitions,
    )

    return StandardResponse(
        data=WorkflowStepResponse.model_validate(step),
        message="Workflow step created successfully",
    )


@router.get(
    "/{workflow_id}/steps",
    response_model=StandardListResponse[WorkflowStepResponse],
    status_code=status.HTTP_200_OK,
    summary="List workflow steps",
    description="List steps for a workflow. Requires workflows.view permission.",
)
async def list_workflow_steps(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    current_user: Annotated[User, Depends(require_permission("workflows.view"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> StandardListResponse[WorkflowStepResponse]:
    """List workflow steps."""
    steps = service.get_workflow_steps(workflow_id, current_user.tenant_id)

    return StandardListResponse(
        data=[WorkflowStepResponse.model_validate(s) for s in steps],
        total=len(steps),
        page=1,
        page_size=len(steps),
        total_pages=1,
        message="Workflow steps retrieved successfully",
    )


@router.post(
    "/{workflow_id}/execute",
    response_model=StandardResponse[WorkflowExecutionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Start workflow execution",
    description="Start a workflow execution. Requires workflows.manage permission.",
)
async def start_workflow_execution(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    execution_data: WorkflowExecutionCreate = ...,
    current_user: Annotated[User, Depends(require_permission("workflows.manage"))],
    service: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> StandardResponse[WorkflowExecutionResponse]:
    """Start a workflow execution."""
    execution = service.start_workflow_execution(
        workflow_id=workflow_id,
        tenant_id=current_user.tenant_id,
        entity_type=execution_data.entity_type,
        entity_id=execution_data.entity_id,
        execution_data=execution_data.execution_data,
    )

    return StandardResponse(
        data=WorkflowExecutionResponse.model_validate(execution),
        message="Workflow execution started successfully",
    )

