"""Approvals router for approval workflow management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.core.approvals.service import ApprovalService
from app.core.auth.dependencies import require_permission
from app.core.auth.rate_limit import limiter
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.models.user import User
from app.schemas.approval import (
    ApprovalActionResponse,
    ApprovalDelegationResponse,
    ApprovalFlowCreate,
    ApprovalFlowResponse,
    ApprovalFlowUpdate,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalStepCreate,
    ApprovalStepResponse,
    ApprovalStepUpdate,
)
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse

router = APIRouter()


def get_approval_service(
    db: Annotated[Session, Depends(get_db)],
) -> ApprovalService:
    """Dependency to get ApprovalService."""
    from app.core.flow_runs.service import FlowRunService

    flow_runs_service = FlowRunService(db)
    return ApprovalService(db, flow_runs_service=flow_runs_service)


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

    # Create response with empty steps (new flow has no steps)
    flow_dict = ApprovalFlowResponse.model_validate(flow).model_dump()
    flow_dict["steps"] = []

    return StandardResponse(
        data=ApprovalFlowResponse(**flow_dict),
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
        meta=PaginationMeta(
            total=total, page=page, page_size=page_size, total_pages=total_pages
        ),
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

    # Get steps for the flow
    steps = service.repository.get_approval_steps_by_flow(
        flow_id, current_user.tenant_id
    )

    # Create response with steps
    flow_dict = ApprovalFlowResponse.model_validate(flow).model_dump()
    flow_dict["steps"] = [ApprovalStepResponse.model_validate(step) for step in steps]

    return StandardResponse(
        data=ApprovalFlowResponse(**flow_dict),
    )


@router.put(
    "/flows/{flow_id}",
    response_model=StandardResponse[ApprovalFlowResponse],
    status_code=status.HTTP_200_OK,
    summary="Update approval flow",
    description="Update an approval flow. Requires approvals.manage permission.",
)
async def update_approval_flow(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    flow_data: ApprovalFlowUpdate,
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalFlowResponse]:
    """Update an approval flow."""
    try:
        flow = service.update_approval_flow(
            flow_id=flow_id,
            flow_data=flow_data.model_dump(exclude_none=True),
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )

        return StandardResponse(
            data=ApprovalFlowResponse.model_validate(flow),
        )
    except ValueError as e:
        error_message = str(e)
        if "not found" in error_message.lower():
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="FLOW_NOT_FOUND",
                message=error_message,
            )
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CANNOT_UPDATE_FLOW",
            message=error_message,
        )


@router.delete(
    "/flows/{flow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete approval flow",
    description="Delete an approval flow. Requires approvals.manage permission.",
)
async def delete_approval_flow(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> None:
    """Delete an approval flow."""
    try:
        service.delete_approval_flow(
            flow_id=flow_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as e:
        error_message = str(e)
        if "not found" in error_message.lower():
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="FLOW_NOT_FOUND",
                message=error_message,
            )
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CANNOT_DELETE_FLOW",
            message=error_message,
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
    )


@router.put(
    "/flows/{flow_id}/steps",
    response_model=StandardResponse[list[ApprovalStepResponse]],
    status_code=status.HTTP_200_OK,
    summary="Update flow steps",
    description="Update all steps in an approval flow. Requires approvals.manage permission.",
)
async def update_flow_steps(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    steps_data: list[ApprovalStepCreate],
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[list[ApprovalStepResponse]]:
    """Update all steps in an approval flow."""
    try:
        # Delete existing steps
        service.delete_all_flow_steps(
            flow_id=flow_id,
            tenant_id=current_user.tenant_id,
        )

        # Create new steps
        created_steps = []
        for step_data in steps_data:
            step = service.add_approval_step(
                flow_id=flow_id,
                tenant_id=current_user.tenant_id,
                step_data=step_data.model_dump(exclude_none=True),
            )
            created_steps.append(step)

        return StandardResponse(
            data=[ApprovalStepResponse.model_validate(step) for step in created_steps],
        )
    except ValueError as e:
        error_message = str(e)
        if "not found" in error_message.lower():
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="FLOW_NOT_FOUND",
                message=error_message,
            )
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CANNOT_UPDATE_STEPS",
            message=error_message,
        )


@router.get(
    "/flows/{flow_id}/steps",
    response_model=StandardListResponse[ApprovalStepResponse],
    status_code=status.HTTP_200_OK,
    summary="List approval steps",
    description="List all steps for an approval flow. Requires approvals.view permission.",
)
async def get_approval_steps(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardListResponse[ApprovalStepResponse]:
    """Get all steps for a flow."""
    steps = service.get_approval_steps_by_flow(flow_id, current_user.tenant_id)

    return StandardListResponse(
        data=[ApprovalStepResponse.model_validate(s) for s in steps],
        meta=PaginationMeta(
            total=len(steps), page=1, page_size=len(steps), total_pages=1
        ),
    )


@router.put(
    "/flows/{flow_id}/steps/{step_id}",
    response_model=StandardResponse[ApprovalStepResponse],
    status_code=status.HTTP_200_OK,
    summary="Update approval step",
    description="Update an approval step. Requires approvals.manage permission.",
)
async def update_approval_step(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    step_id: Annotated[UUID, Path(..., description="Approval step ID")],
    step_data: ApprovalStepUpdate,
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalStepResponse]:
    """Update an approval step."""
    try:
        step = service.update_approval_step(
            step_id=step_id,
            flow_id=flow_id,
            step_data=step_data.model_dump(exclude_none=True),
            tenant_id=current_user.tenant_id,
        )

        return StandardResponse(
            data=ApprovalStepResponse.model_validate(step),
        )
    except ValueError as e:
        error_message = str(e)
        if "not found" in error_message.lower():
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="STEP_NOT_FOUND",
                message=error_message,
            )
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CANNOT_UPDATE_STEP",
            message=error_message,
        )


@router.delete(
    "/flows/{flow_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete approval step",
    description="Delete an approval step. Requires approvals.manage permission.",
)
async def delete_approval_step(
    flow_id: Annotated[UUID, Path(..., description="Approval flow ID")],
    step_id: Annotated[UUID, Path(..., description="Approval step ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> None:
    """Delete an approval step."""
    try:
        service.delete_approval_step(
            step_id=step_id,
            flow_id=flow_id,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as e:
        error_message = str(e)
        if "not found" in error_message.lower():
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="STEP_NOT_FOUND",
                message=error_message,
            )
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CANNOT_DELETE_STEP",
            message=error_message,
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
        meta=PaginationMeta(
            total=total, page=page, page_size=page_size, total_pages=total_pages
        ),
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
    )


@router.post(
    "/requests/{request_id}/approve",
    response_model=StandardResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Approve request",
    description="Approve an approval request. Requires approvals.approve permission.",
)
@limiter.limit("10/minute")
async def approve_request(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.approve"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    request: Request,
    comment: Annotated[str | None, Query(description="Optional comment")] = None,
) -> StandardResponse[ApprovalRequestResponse]:
    """Approve an approval request."""
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        approval_request = service.approve_request(
            request_id=request_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            comment=comment,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return StandardResponse(
            data=ApprovalRequestResponse.model_validate(approval_request),
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
@limiter.limit("10/minute")
async def reject_request(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.approve"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    request: Request,
    comment: Annotated[str | None, Query(description="Optional comment")] = None,
) -> StandardResponse[ApprovalRequestResponse]:
    """Reject an approval request."""
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        approval_request = service.reject_request(
            request_id=request_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            comment=comment,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return StandardResponse(
            data=ApprovalRequestResponse.model_validate(approval_request),
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_REQUEST_NOT_FOUND",
            message=str(e),
        )


@router.post(
    "/requests/{request_id}/cancel",
    response_model=StandardResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel request",
    description="Cancel an approval request. Requires approvals.manage permission.",
)
async def cancel_request(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[ApprovalRequestResponse]:
    """Cancel an approval request."""
    try:
        request = service.cancel_request(
            request_id=request_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )

        return StandardResponse(
            data=ApprovalRequestResponse.model_validate(request),
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="CANNOT_CANCEL_REQUEST",
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
        meta=PaginationMeta(
            total=len(actions), page=1, page_size=len(actions), total_pages=1
        ),
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
    expires_at: datetime | None = Query(
        default=None, description="Delegation expiration"
    ),
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
    )


@router.get(
    "/requests/{request_id}/delegations",
    response_model=StandardListResponse[ApprovalDelegationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get request delegations",
    description="Get delegations for an approval request. Requires approvals.view permission.",
)
async def get_request_delegations(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardListResponse[ApprovalDelegationResponse]:
    """Get delegations for a request."""
    delegations = service.get_delegations(request_id, current_user.tenant_id)

    return StandardListResponse(
        data=[ApprovalDelegationResponse.model_validate(d) for d in delegations],
        meta=PaginationMeta(
            total=len(delegations), page=1, page_size=len(delegations), total_pages=1
        ),
    )


@router.get(
    "/stats",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get approval statistics",
    description="Get approval statistics for the tenant. Requires approvals.view permission.",
)
async def get_approval_stats(
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[dict]:
    """Get approval statistics."""
    stats = service.get_approval_stats(current_user.tenant_id)

    return StandardResponse(
        data=stats,
    )


@router.get(
    "/requests/{request_id}/timeline",
    response_model=StandardResponse[list[dict]],
    status_code=status.HTTP_200_OK,
    summary="Get request timeline",
    description="Get timeline of actions and delegations for a request. Requires approvals.view permission.",
)
async def get_request_timeline(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[list[dict]]:
    """Get timeline for a request."""
    try:
        timeline = service.get_request_timeline(request_id, current_user.tenant_id)

        return StandardResponse(
            data=timeline,
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_REQUEST_NOT_FOUND",
            message=str(e),
        )


# Integration endpoints for widgets and entity-based operations
@router.post(
    "/requests/by-entity",
    response_model=StandardResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Get or create request by entity",
    description="Get existing approval request or create new one for an entity. Requires approvals.manage permission.",
)
async def get_or_create_request_by_entity(
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    entity_type: Annotated[
        str, Query(description="Entity type (e.g., 'order', 'invoice')")
    ] = ...,
    entity_id: Annotated[UUID, Query(description="Entity ID")] = ...,
    auto_create: Annotated[
        bool, Query(description="Auto-create request if none exists")
    ] = False,
    flow_id: Annotated[
        UUID | None, Query(description="Flow ID (required if auto_create=True)")
    ] = None,
    title: Annotated[
        str | None, Query(description="Request title (required if auto_create=True)")
    ] = None,
    description: Annotated[str | None, Query(description="Request description")] = None,
) -> StandardResponse[ApprovalRequestResponse]:
    """Get or create approval request for an entity."""
    try:
        request = service.get_or_create_request_by_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            auto_create=auto_create,
            flow_id=flow_id,
            title=title,
            description=description,
        )

        if not request:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="APPROVAL_REQUEST_NOT_FOUND",
                message="No approval request found for this entity",
            )

        return StandardResponse(
            data=ApprovalRequestResponse.model_validate(request),
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_REQUEST",
            message=str(e),
        )


@router.get(
    "/requests/{request_id}/widget-data",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get widget data",
    description="Get all data needed for the approval widget in a single call. Requires approvals.view permission.",
)
async def get_request_widget_data(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[dict]:
    """Get widget data for a request."""
    try:
        widget_data = service.get_request_widget_data(
            request_id=request_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )

        return StandardResponse(
            data=widget_data,
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_REQUEST_NOT_FOUND",
            message=str(e),
        )


@router.get(
    "/requests/by-entity-status",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get entity approval status",
    description="Get approval status for an entity without creating a request. Requires approvals.view permission.",
)
async def get_entity_approval_status(
    entity_type: Annotated[
        str, Query(..., description="Entity type (e.g., 'order', 'invoice')")
    ],
    entity_id: Annotated[UUID, Query(..., description="Entity ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[dict]:
    """Get approval status for an entity."""
    status_data = service.get_entity_approval_status(
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
    )

    return StandardResponse(
        data=status_data,
    )


@router.get(
    "/requests/{request_id}/can-approve",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Check if user can approve",
    description="Check if the current user can approve a specific request. Requires approvals.view permission.",
)
async def check_user_can_approve(
    request_id: Annotated[UUID, Path(..., description="Approval request ID")],
    current_user: Annotated[User, Depends(require_permission("approvals.view"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> StandardResponse[dict]:
    """Check if user can approve a request."""
    try:
        can_approve_data = service.user_can_approve_step(
            request_id=request_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
        )

        return StandardResponse(
            data=can_approve_data,
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="APPROVAL_REQUEST_NOT_FOUND",
            message=str(e),
        )


# Bulk operations endpoints
@router.post(
    "/requests/bulk-approve",
    response_model=StandardListResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Bulk approve requests",
    description="Approve multiple approval requests. Requires approvals.manage permission.",
)
async def bulk_approve_requests(
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    request: Request,
    request_ids: Annotated[
        list[UUID], Query(..., description="List of request IDs to approve")
    ] = ...,
    comment: Annotated[
        str | None, Query(description="Optional comment for all approvals")
    ] = None,
) -> StandardListResponse[ApprovalRequestResponse]:
    """Bulk approve approval requests."""
    try:
        approved_requests = service.bulk_approve_requests(
            request_ids=request_ids,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            comment=comment,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return StandardListResponse(
            data=[ApprovalRequestResponse.model_validate(r) for r in approved_requests],
            meta=PaginationMeta(
                total=len(approved_requests),
                page=1,
                page_size=len(approved_requests),
                total_pages=1,
            ),
        )
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BULK_APPROVE_FAILED",
            message=str(e),
        )


@router.post(
    "/requests/bulk-reject",
    response_model=StandardListResponse[ApprovalRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="Bulk reject requests",
    description="Reject multiple approval requests. Requires approvals.manage permission.",
)
async def bulk_reject_requests(
    current_user: Annotated[User, Depends(require_permission("approvals.manage"))],
    service: Annotated[ApprovalService, Depends(get_approval_service)],
    request: Request,
    request_ids: Annotated[
        list[UUID], Query(..., description="List of request IDs to reject")
    ] = ...,
    comment: Annotated[
        str | None, Query(description="Optional comment for all rejections")
    ] = None,
) -> StandardListResponse[ApprovalRequestResponse]:
    """Bulk reject approval requests."""
    try:
        rejected_requests = service.bulk_reject_requests(
            request_ids=request_ids,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            comment=comment,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return StandardListResponse(
            data=[ApprovalRequestResponse.model_validate(r) for r in rejected_requests],
            meta=PaginationMeta(
                total=len(rejected_requests),
                page=1,
                page_size=len(rejected_requests),
                total_pages=1,
            ),
        )
    except Exception as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="BULK_REJECT_FAILED",
            message=str(e),
        )
