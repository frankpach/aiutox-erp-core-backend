from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.models.user import User
from app.modules.crm.schemas.crm import (
    LeadCreate,
    LeadResponse,
    LeadUpdate,
    OpportunityCreate,
    OpportunityResponse,
    OpportunityUpdate,
    PipelineCreate,
    PipelineResponse,
    PipelineUpdate,
)
from app.modules.crm.services.crm_service import CRMService
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse

router = APIRouter()


def get_crm_service(db: Annotated[Session, Depends(get_db)]) -> CRMService:
    return CRMService(db)


# Pipelines
@router.get(
    "/pipelines",
    response_model=StandardListResponse[PipelineResponse],
    status_code=status.HTTP_200_OK,
    summary="List pipelines",
    description="List CRM pipelines. Requires crm.view permission.",
)
async def list_pipelines(
    current_user: Annotated[User, Depends(require_permission("crm.view"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> StandardListResponse[PipelineResponse]:
    skip = (page - 1) * page_size
    pipelines = service.list_pipelines(current_user.tenant_id, skip=skip, limit=page_size)
    total = len(pipelines)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return StandardListResponse(
        data=[PipelineResponse.model_validate(p) for p in pipelines],
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.post(
    "/pipelines",
    response_model=StandardResponse[PipelineResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create pipeline",
    description="Create CRM pipeline. Requires crm.create permission.",
)
async def create_pipeline(
    payload: PipelineCreate,
    current_user: Annotated[User, Depends(require_permission("crm.create"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[PipelineResponse]:
    pipeline = service.create_pipeline(current_user.tenant_id, payload.model_dump())
    return StandardResponse(data=PipelineResponse.model_validate(pipeline))


@router.get(
    "/pipelines/{pipeline_id}",
    response_model=StandardResponse[PipelineResponse],
    status_code=status.HTTP_200_OK,
    summary="Get pipeline",
    description="Get CRM pipeline. Requires crm.view permission.",
)
async def get_pipeline(
    pipeline_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("crm.view"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[PipelineResponse]:
    pipeline = service.get_pipeline(current_user.tenant_id, pipeline_id)
    return StandardResponse(data=PipelineResponse.model_validate(pipeline))


@router.put(
    "/pipelines/{pipeline_id}",
    response_model=StandardResponse[PipelineResponse],
    status_code=status.HTTP_200_OK,
    summary="Update pipeline",
    description="Update CRM pipeline. Requires crm.edit permission.",
)
async def update_pipeline(
    pipeline_id: Annotated[UUID, Path(...)],
    payload: PipelineUpdate,
    current_user: Annotated[User, Depends(require_permission("crm.edit"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[PipelineResponse]:
    pipeline = service.update_pipeline(
        tenant_id=current_user.tenant_id,
        pipeline_id=pipeline_id,
        data=payload.model_dump(exclude_unset=True),
    )
    return StandardResponse(data=PipelineResponse.model_validate(pipeline))


@router.delete(
    "/pipelines/{pipeline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete pipeline",
    description="Delete CRM pipeline. Requires crm.delete permission.",
)
async def delete_pipeline(
    pipeline_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("crm.delete"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> None:
    service.delete_pipeline(current_user.tenant_id, pipeline_id)


# Leads
@router.get(
    "/leads",
    response_model=StandardListResponse[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="List leads",
    description="List CRM leads. Requires crm.view permission.",
)
async def list_leads(
    current_user: Annotated[User, Depends(require_permission("crm.view"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
    status_filter: str | None = Query(default=None, alias="status"),
    pipeline_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> StandardListResponse[LeadResponse]:
    skip = (page - 1) * page_size
    leads = service.list_leads(
        tenant_id=current_user.tenant_id,
        status=status_filter,
        pipeline_id=pipeline_id,
        skip=skip,
        limit=page_size,
    )
    total = len(leads)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return StandardListResponse(
        data=[LeadResponse.model_validate(lead) for lead in leads],
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.post(
    "/leads",
    response_model=StandardResponse[LeadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create lead",
    description="Create CRM lead. Requires crm.create permission.",
)
async def create_lead(
    payload: LeadCreate,
    current_user: Annotated[User, Depends(require_permission("crm.create"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[LeadResponse]:
    lead = service.create_lead(current_user.tenant_id, current_user.id, payload.model_dump())
    return StandardResponse(data=LeadResponse.model_validate(lead))


@router.get(
    "/leads/{lead_id}",
    response_model=StandardResponse[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Get lead",
    description="Get CRM lead. Requires crm.view permission.",
)
async def get_lead(
    lead_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("crm.view"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[LeadResponse]:
    lead = service.get_lead(current_user.tenant_id, lead_id)
    return StandardResponse(data=LeadResponse.model_validate(lead))


@router.put(
    "/leads/{lead_id}",
    response_model=StandardResponse[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Update lead",
    description="Update CRM lead. Requires crm.edit permission.",
)
async def update_lead(
    lead_id: Annotated[UUID, Path(...)],
    payload: LeadUpdate,
    current_user: Annotated[User, Depends(require_permission("crm.edit"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[LeadResponse]:
    lead = service.update_lead(
        tenant_id=current_user.tenant_id,
        lead_id=lead_id,
        data=payload.model_dump(exclude_unset=True),
    )
    return StandardResponse(data=LeadResponse.model_validate(lead))


@router.delete(
    "/leads/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead",
    description="Delete CRM lead. Requires crm.delete permission.",
)
async def delete_lead(
    lead_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("crm.delete"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> None:
    service.delete_lead(current_user.tenant_id, lead_id)


# Opportunities
@router.get(
    "/opportunities",
    response_model=StandardListResponse[OpportunityResponse],
    status_code=status.HTTP_200_OK,
    summary="List opportunities",
    description="List CRM opportunities. Requires crm.view permission.",
)
async def list_opportunities(
    current_user: Annotated[User, Depends(require_permission("crm.view"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
    status_filter: str | None = Query(default=None, alias="status"),
    pipeline_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> StandardListResponse[OpportunityResponse]:
    skip = (page - 1) * page_size
    opps = service.list_opportunities(
        tenant_id=current_user.tenant_id,
        status=status_filter,
        pipeline_id=pipeline_id,
        skip=skip,
        limit=page_size,
    )
    total = len(opps)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return StandardListResponse(
        data=[OpportunityResponse.model_validate(o) for o in opps],
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.post(
    "/opportunities",
    response_model=StandardResponse[OpportunityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create opportunity",
    description="Create CRM opportunity. Requires crm.create permission.",
)
async def create_opportunity(
    payload: OpportunityCreate,
    current_user: Annotated[User, Depends(require_permission("crm.create"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[OpportunityResponse]:
    opp = service.create_opportunity(current_user.tenant_id, current_user.id, payload.model_dump())
    return StandardResponse(data=OpportunityResponse.model_validate(opp))


@router.get(
    "/opportunities/{opportunity_id}",
    response_model=StandardResponse[OpportunityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get opportunity",
    description="Get CRM opportunity. Requires crm.view permission.",
)
async def get_opportunity(
    opportunity_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("crm.view"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[OpportunityResponse]:
    opp = service.get_opportunity(current_user.tenant_id, opportunity_id)
    return StandardResponse(data=OpportunityResponse.model_validate(opp))


@router.put(
    "/opportunities/{opportunity_id}",
    response_model=StandardResponse[OpportunityResponse],
    status_code=status.HTTP_200_OK,
    summary="Update opportunity",
    description="Update CRM opportunity. Requires crm.edit permission.",
)
async def update_opportunity(
    opportunity_id: Annotated[UUID, Path(...)],
    payload: OpportunityUpdate,
    current_user: Annotated[User, Depends(require_permission("crm.edit"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> StandardResponse[OpportunityResponse]:
    opp = service.update_opportunity(
        tenant_id=current_user.tenant_id,
        opportunity_id=opportunity_id,
        data=payload.model_dump(exclude_unset=True),
    )
    return StandardResponse(data=OpportunityResponse.model_validate(opp))


@router.delete(
    "/opportunities/{opportunity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete opportunity",
    description="Delete CRM opportunity. Requires crm.delete permission.",
)
async def delete_opportunity(
    opportunity_id: Annotated[UUID, Path(...)],
    current_user: Annotated[User, Depends(require_permission("crm.delete"))],
    service: Annotated[CRMService, Depends(get_crm_service)],
) -> None:
    service.delete_opportunity(current_user.tenant_id, opportunity_id)
