"""Approvals router for approval workflow management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.approvals.service import ApprovalService
from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.tasks.service import TaskService
from app.models.user import User
from app.schemas.approval import (
    ApprovalActionCreate,
    ApprovalActionResponse,
    ApprovalDelegationCreate,
    ApprovalDelegationResponse,
    ApprovalFlowCreate,
    ApprovalFlowResponse,
    ApprovalFlowUpdate,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalStepCreate,
    ApprovalStepResponse,
)
from app.schemas.common import StandardListResponse, StandardResponse

router = APIRouter()


def get_approval_service(
    db: Annotated[Session, Depends(get_db)],
) -> ApprovalService:
    """Dependency to get ApprovalService."""
    return ApprovalService(db)


# Approval Flow endpoints
@router.post(
    "/flows",
    response_model=StandardResponse[ApprovalFlowResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create approval flow",
    description="Create a new approval flow. Requires approvals.manage permission.",
)
async def create_approval_flow(
    flow_data: ApprovalFlowCreate,
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalFlowResponse]:
    """Create a new approval flow."""
    flow = service.create_approval_flow(
        flow_data=flow_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=ApprovalFlowResponse.model_validate(flow),
        message="Approval flow created successfully",
    )


@router.get(
    "/flows",
    response_model=StandardListResponse[ApprovalFlowResponse],
    status_code=status.HTTP_200_OK,
    summary="List approval flows",
    description="List approval flows. Requires approvals.view permission.",
)
async def list_approval_flows(
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    module: str | None = Query(None, description="Filter by module"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ApprovalFlowResponse]:
    """List approval flows."""
    skip = (page - 1) * page_size
    flows = service.get_approval_flows(
        tenant_id=current_user.tenant_id,
        module=module,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    total = len(flows)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ApprovalFlowResponse.model_validate(f) for f in flows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Approval flows retrieved successfully",
    )


@router.get(
    "/flows/{flow_id}",
    response_model=StandardResponse[ApprovalFlowResponse],
    status_code=status.HTTP_200_OK,
    summary="Get approval flow",
    description="Get a specific approval flow by ID. Requires approvals.view permission.",
)
async def get_approval_flow(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalFlowResponse]:
    """Get a specific approval flow."""
    flow = service.get_approval_flow(flow_id, current_user.tenant_id)
    if not flow:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_FLOW_NOT_FOUND",
            message=f"Approval flow with ID {flow_id} not found",
        )

    return StandardResponse(
        data=ApprovalFlowResponse.model_validate(flow),
        message="Approval flow retrieved successfully",
    )


@router.post(
    "/flows/{flow_id}/steps",
    response_model=StandardResponse[ApprovalStepResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add approval step",
    description="Add a step to an approval flow. Requires approvals.manage permission.",
)
async def add_approval_step(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    step_data: ApprovalStepCreate,
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalStepResponse]:
    """Add a step to an approval flow."""
    step = service.add_approval_step(
        flow_id=flow_id,
        tenant_id=current_user.tenant_id,
        step_data=step_data.model_dump(exclude_none=True),
    )

    return StandardResponse(
        data=ApprovalStepResponse.model_validate(step),
        message="Approval step added successfully",
    )


# Approval Request endpoints
@router.post(
    "/requests",
    response_model=StandardResponse[ApprovalRequestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create approval request",
    description="Create a new approval request. Requires approvals.manage permission.",
)
async def create_approval_request(
    request_data: ApprovalRequestCreate,
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalRequestResponse]:
    """Create a new approval request."""
    request = service.create_approval_request(
        request_data=request_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=ApprovalRequestResponse.model_validate(request),
        message="Approval request created successfully",
    )


@router.get(
    "/requests",
    response_model=StandardListResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List approval requests",
    description="List approval requests. Requires approvals.view permission.",
)
async def list_approval_requests(
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    flow_id: UUID | None = Query(None, description="Filter by flow ID"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ApprovalRequestResponse]:
    """List approval requests."""
    skip = (page - 1) * page_size
    requests = service.get_approval_requests(
        tenant_id=current_user.tenant_id,
        flow_id=flow_id,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        requested_by=current_user.id,
        skip=skip,
        limit=page_size,
    )

    total = len(requests)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ApprovalRequestResponse.model_validate(r) for r in requests],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Approval requests retrieved successfully",
    )


@router.get(
    "/requests/{request_id}",
    response_model=StandardResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Get approval request",
    description="Get a specific approval request by ID. Requires approvals.view permission.",
)
async def get_approval_request(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalRequestResponse]:
    """Get a specific approval request."""
    request = service.get_approval_request(request_id, current_user.tenant_id)
    if not request:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_REQUEST_NOT_FOUND",
            message=f"Approval request with ID {request_id} not found",
        )

    return StandardResponse(
        data=ApprovalRequestResponse.model_validate(request),
        message="Approval request retrieved successfully",
    )


@router.post(
    "/requests/{request_id}/approve",
    response_model=StandardResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Approve request",
    description="Approve an approval request. Requires approvals.approve permission.",
)
async def approve_request(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.approve"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    comment: Annotated[str | None, Query(description="Optional comment")] = None,
) -> StandardResponse[ApprovalRequestResponse]:
    """Approve an approval request."""
    try:
        request = service.approve_request(
            request_id=request_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            comment=comment,
        )

        return StandardResponse(
            data=ApprovalRequestResponse.model_validate(request),
            message="Request approved successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_REQUEST_NOT_FOUND",
            message=str(e),
        )


@router.post(
    "/requests/{request_id}/reject",
    response_model=StandardResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Reject request",
    description="Reject an approval request. Requires approvals.approve permission.",
)
async def reject_request(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.approve"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    comment: Annotated[str | None, Query(description="Optional comment")] = None,
) -> StandardResponse[ApprovalRequestResponse]:
    """Reject an approval request."""
    try:
        request = service.reject_request(
            request_id=request_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            comment=comment,
        )

        return StandardResponse(
            data=ApprovalRequestResponse.model_validate(request),
            message="Request rejected successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_REQUEST_NOT_FOUND",
            message=str(e),
        )


@router.get(
    "/requests/{request_id}/actions",
    response_model=StandardListResponse[ApprovalActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get approval actions",
    description="Get approval actions for a request. Requires approvals.view permission.",
)
async def get_approval_actions(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardListResponse[ApprovalActionResponse]:
    """Get approval actions for a request."""
    actions = service.get_approval_actions(request_id, current_user.tenant_id)

    return StandardListResponse(
        data=[ApprovalActionResponse.model_validate(a) for a in actions],
        total=len(actions),
        page=1,
        page_size=len(actions),
        total_pages=1,
        message="Approval actions retrieved successfully",
    )


# Approval Delegation endpoints
@router.post(
    "/requests/{request_id}/delegate",
    response_model=StandardResponse[ApprovalDelegationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Delegate approval",
    description="Delegate an approval to another user. Requires approvals.delegate permission.",
)
async def delegate_approval(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    to_user_id: Annotated[UUID, Query(..., description="User ID to delegate to")],
    current_user: Annotated[User, Depends(require_permission("approvals.delegate"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    reason: str | None = Query(default=None, description="Delegation reason"),
    expires_at: datetime | None = Query(default=None, description="Delegation expiration"),
) -> StandardResponse[ApprovalDelegationResponse]:
    """Delegate an approval to another user."""
    delegation = service.delegate_approval(
        request_id=request_id,
        tenant_id=current_user.tenant_id,
        from_user_id=current_user.id,
        to_user_id=to_user_id,
        reason=reason,
        expires_at=expires_at,
    )

    return StandardResponse(
        data=ApprovalDelegationResponse.model_validate(delegation),
        message="Approval delegated successfully",
    )


