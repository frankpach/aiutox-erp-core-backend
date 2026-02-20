"""Reporting router for report management."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.reporting.service import ReportingService
from app.core.reporting.sources.products_data_source import ProductsDataSource
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.reporting import (
    ReportDefinitionCreate,
    ReportDefinitionResponse,
    ReportDefinitionUpdate,
    ReportExecutionRequest,
    ReportExecutionResponse,
)

router = APIRouter()


def get_reporting_service(
    db: Annotated[Session, Depends(get_db)],
) -> ReportingService:
    """Dependency to get ReportingService."""
    service = ReportingService(db)
    # Register data sources
    service.engine.register_data_source("products", ProductsDataSource)
    return service


@router.post(
    "/reports",
    response_model=StandardResponse[ReportDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create report",
    description="Create a new report definition. Requires reporting.manage permission.",
)
async def create_report(
    report_data: ReportDefinitionCreate,
    current_user: Annotated[User, Depends(require_permission("reporting.manage"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
) -> StandardResponse[ReportDefinitionResponse]:
    """Create a new report definition."""
    report = service.create_report(
        tenant_id=current_user.tenant_id,
        name=report_data.name,
        description=report_data.description,
        data_source_type=report_data.data_source_type,
        visualization_type=report_data.visualization_type,
        created_by=current_user.id,
        filters=report_data.filters,
        config=report_data.config,
    )

    return StandardResponse(
        data=ReportDefinitionResponse.model_validate(report),
        message="Report created successfully",
    )


@router.get(
    "/reports",
    response_model=StandardListResponse[ReportDefinitionResponse],
    status_code=status.HTTP_200_OK,
    summary="List reports",
    description="List all reports for the current tenant. Requires reporting.view permission.",
)
async def list_reports(
    current_user: Annotated[User, Depends(require_permission("reporting.view"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ReportDefinitionResponse]:
    """List all reports."""
    skip = (page - 1) * page_size
    reports = service.get_all_reports(
        tenant_id=current_user.tenant_id, skip=skip, limit=page_size
    )

    total = len(reports)  # TODO: Add count method to repository
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ReportDefinitionResponse.model_validate(report) for report in reports],
        meta={
            "total": total,
            "page": page,
            "page_size": (
                max(page_size, 1) if total == 0 else page_size
            ),  # Minimum page_size is 1
            "total_pages": total_pages,
        },
    )


@router.get(
    "/reports/{report_id}",
    response_model=StandardResponse[ReportDefinitionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get report",
    description="Get a specific report by ID. Requires reporting.view permission.",
)
async def get_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(require_permission("reporting.view"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
) -> StandardResponse[ReportDefinitionResponse]:
    """Get a specific report."""
    report = service.get_report(report_id, current_user.tenant_id)
    if not report:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="REPORTING_REPORT_NOT_FOUND",
            message=f"Report with ID {report_id} not found",
        )

    return StandardResponse(
        data=ReportDefinitionResponse.model_validate(report),
        message="Report retrieved successfully",
    )


@router.put(
    "/reports/{report_id}",
    response_model=StandardResponse[ReportDefinitionResponse],
    status_code=status.HTTP_200_OK,
    summary="Update report",
    description="Update a report definition. Requires reporting.manage permission.",
)
async def update_report(
    report_id: UUID,
    report_data: ReportDefinitionUpdate,
    current_user: Annotated[User, Depends(require_permission("reporting.manage"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
) -> StandardResponse[ReportDefinitionResponse]:
    """Update a report definition."""
    report = service.update_report(
        report_id=report_id,
        tenant_id=current_user.tenant_id,
        name=report_data.name,
        description=report_data.description,
        filters=report_data.filters,
        config=report_data.config,
    )

    if not report:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="REPORTING_REPORT_NOT_FOUND",
            message=f"Report with ID {report_id} not found",
        )

    return StandardResponse(
        data=ReportDefinitionResponse.model_validate(report),
        message="Report updated successfully",
    )


@router.delete(
    "/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report",
    description="Delete a report definition. Requires reporting.manage permission.",
)
async def delete_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(require_permission("reporting.manage"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
) -> None:
    """Delete a report definition."""
    deleted = service.delete_report(report_id, current_user.tenant_id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="REPORTING_REPORT_NOT_FOUND",
            message=f"Report with ID {report_id} not found",
        )


@router.post(
    "/reports/{report_id}/execute",
    response_model=StandardResponse[ReportExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute report",
    description="Execute a report and get results. Requires reporting.view permission.",
)
async def execute_report(
    report_id: UUID,
    execution_data: ReportExecutionRequest,
    current_user: Annotated[User, Depends(require_permission("reporting.view"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
) -> StandardResponse[ReportExecutionResponse]:
    """Execute a report."""
    try:
        result = await service.execute_report(
            report_id=report_id,
            tenant_id=current_user.tenant_id,
            filters=execution_data.filters,
            pagination=execution_data.pagination,
        )
        return StandardResponse(
            data=ReportExecutionResponse(**result),
            message="Report executed successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="REPORTING_REPORT_NOT_FOUND",
            message=str(e),
        )


@router.get(
    "/data-sources",
    response_model=StandardResponse[list[dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="List data sources",
    description="List available data sources. Requires reporting.view permission.",
)
async def list_data_sources(
    current_user: Annotated[User, Depends(require_permission("reporting.view"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
) -> StandardResponse[list[dict[str, Any]]]:
    """List available data sources."""
    # Return registered data sources
    data_sources = [
        {"type": source_type, "name": source_type.capitalize()}
        for source_type in service.engine._data_sources.keys()
    ]

    return StandardResponse(
        data=data_sources,
        message="Data sources retrieved successfully",
    )


@router.get(
    "/data-sources/{source_type}/columns",
    response_model=StandardResponse[list[dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="Get data source columns",
    description="Get available columns for a data source. Requires reporting.view permission.",
)
async def get_data_source_columns(
    source_type: str,
    current_user: Annotated[User, Depends(require_permission("reporting.view"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[list[dict[str, Any]]]:
    """Get columns for a data source."""
    data_source_class = service.engine._data_sources.get(source_type)
    if not data_source_class:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="REPORTING_DATA_SOURCE_NOT_FOUND",
            message=f"Data source type '{source_type}' not found",
        )

    # Create temporary instance to get columns
    data_source = data_source_class(db, current_user.tenant_id)
    columns = data_source.get_columns()

    return StandardResponse(
        data=columns,
        message="Columns retrieved successfully",
    )


@router.get(
    "/data-sources/{source_type}/filters",
    response_model=StandardResponse[list[dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="Get data source filters",
    description="Get available filters for a data source. Requires reporting.view permission.",
)
async def get_data_source_filters(
    source_type: str,
    current_user: Annotated[User, Depends(require_permission("reporting.view"))],
    service: Annotated[ReportingService, Depends(get_reporting_service)],
    db: Annotated[Session, Depends(get_db)],
) -> StandardResponse[list[dict[str, Any]]]:
    """Get filters for a data source."""
    data_source_class = service.engine._data_sources.get(source_type)
    if not data_source_class:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="REPORTING_DATA_SOURCE_NOT_FOUND",
            message=f"Data source type '{source_type}' not found",
        )

    # Create temporary instance to get filters
    data_source = data_source_class(db, current_user.tenant_id)
    filters = data_source.get_filters()

    return StandardResponse(
        data=filters,
        message="Filters retrieved successfully",
    )
