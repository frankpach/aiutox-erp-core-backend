"""Import/Export router for data import and export management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File as FastAPIFile, Path, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.import_export.service import ImportExportService
from app.core.files.service import FileService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.import_export import (
    ExportJobCreate,
    ExportJobResponse,
    ImportJobCreate,
    ImportJobResponse,
    ImportTemplateCreate,
    ImportTemplateResponse,
    ImportTemplateUpdate,
)

router = APIRouter()


def get_import_export_service(
    db: Annotated[Session, Depends(get_db)],
) -> ImportExportService:
    """Dependency to get ImportExportService."""
    return ImportExportService(db)


# Import Job endpoints
@router.post(
    "/import/jobs",
    response_model=StandardResponse[ImportJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create import job",
    description="Create a new import job. Requires import_export.import permission.",
)
async def create_import_job(
    job_data: ImportJobCreate,
    current_user: Annotated[User, Depends(require_permission("import_export.import"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[ImportJobResponse]:
    """Create a new import job."""
    job = service.create_import_job(
        job_data=job_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=ImportJobResponse.model_validate(job),
        message="Import job created successfully",
    )


@router.get(
    "/import/jobs",
    response_model=StandardListResponse[ImportJobResponse],
    status_code=status.HTTP_200_OK,
    summary="List import jobs",
    description="List import jobs. Requires import_export.view permission.",
)
async def list_import_jobs(
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
    module: str | None = Query(None, description="Filter by module"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ImportJobResponse]:
    """List import jobs."""
    skip = (page - 1) * page_size
    jobs = service.repository.get_import_jobs(
        tenant_id=current_user.tenant_id,
        module=module,
        status=status,
        skip=skip,
        limit=page_size,
    )

    total = len(jobs)  # TODO: Add count method
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ImportJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Import jobs retrieved successfully",
    )


@router.get(
    "/import/jobs/{job_id}",
    response_model=StandardResponse[ImportJobResponse],
    status_code=status.HTTP_200_OK,
    summary="Get import job",
    description="Get a specific import job by ID. Requires import_export.view permission.",
)
async def get_import_job(
    job_id: UUID = Path(..., description="Import job ID"),
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[ImportJobResponse]:
    """Get a specific import job."""
    job = service.get_import_job(job_id, current_user.tenant_id)
    if not job:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="IMPORT_JOB_NOT_FOUND",
            message=f"Import job with ID {job_id} not found",
        )

    return StandardResponse(
        data=ImportJobResponse.model_validate(job),
        message="Import job retrieved successfully",
    )


# Import Template endpoints
@router.post(
    "/import/templates",
    response_model=StandardResponse[ImportTemplateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create import template",
    description="Create a new import template. Requires import_export.manage permission.",
)
async def create_import_template(
    template_data: ImportTemplateCreate,
    current_user: Annotated[User, Depends(require_permission("import_export.manage"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[ImportTemplateResponse]:
    """Create a new import template."""
    template = service.create_import_template(
        template_data=template_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=ImportTemplateResponse.model_validate(template),
        message="Import template created successfully",
    )


@router.get(
    "/import/templates",
    response_model=StandardListResponse[ImportTemplateResponse],
    status_code=status.HTTP_200_OK,
    summary="List import templates",
    description="List import templates. Requires import_export.view permission.",
)
async def list_import_templates(
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
    module: str | None = Query(None, description="Filter by module"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ImportTemplateResponse]:
    """List import templates."""
    skip = (page - 1) * page_size
    templates = service.get_import_templates(
        tenant_id=current_user.tenant_id,
        module=module,
        skip=skip,
        limit=page_size,
    )

    total = len(templates)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ImportTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Import templates retrieved successfully",
    )


# Export Job endpoints
@router.post(
    "/export/jobs",
    response_model=StandardResponse[ExportJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create export job",
    description="Create a new export job. Requires import_export.export permission.",
)
async def create_export_job(
    job_data: ExportJobCreate,
    current_user: Annotated[User, Depends(require_permission("import_export.export"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[ExportJobResponse]:
    """Create a new export job."""
    job = service.create_export_job(
        job_data=job_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    return StandardResponse(
        data=ExportJobResponse.model_validate(job),
        message="Export job created successfully",
    )


@router.get(
    "/export/jobs",
    response_model=StandardListResponse[ExportJobResponse],
    status_code=status.HTTP_200_OK,
    summary="List export jobs",
    description="List export jobs. Requires import_export.view permission.",
)
async def list_export_jobs(
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
    module: str | None = Query(None, description="Filter by module"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ExportJobResponse]:
    """List export jobs."""
    skip = (page - 1) * page_size
    jobs = service.repository.get_export_jobs(
        tenant_id=current_user.tenant_id,
        module=module,
        status=status,
        skip=skip,
        limit=page_size,
    )

    total = len(jobs)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ExportJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Export jobs retrieved successfully",
    )


@router.get(
    "/export/jobs/{job_id}",
    response_model=StandardResponse[ExportJobResponse],
    status_code=status.HTTP_200_OK,
    summary="Get export job",
    description="Get a specific export job by ID. Requires import_export.view permission.",
)
async def get_export_job(
    job_id: UUID = Path(..., description="Export job ID"),
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[ExportJobResponse]:
    """Get a specific export job."""
    job = service.get_export_job(job_id, current_user.tenant_id)
    if not job:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="EXPORT_JOB_NOT_FOUND",
            message=f"Export job with ID {job_id} not found",
        )

    return StandardResponse(
        data=ExportJobResponse.model_validate(job),
        message="Export job retrieved successfully",
    )

