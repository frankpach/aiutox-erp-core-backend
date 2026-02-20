"""Import/Export router for data import and export management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, UploadFile, status
from fastapi import File as FastAPIFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.import_export.service import ImportExportService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.import_export import (
    ExportJobCreate,
    ExportJobResponse,
    ImportJobCreate,
    ImportJobResponse,
    ImportTemplateCreate,
    ImportTemplateResponse,
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


@router.post(
    "/import/upload",
    response_model=StandardResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Upload file for import",
    description="Upload a file to be used for an import job. Requires import_export.import permission.",
)
async def upload_import_file(
    file: Annotated[UploadFile, FastAPIFile(..., description="File to upload")],
    current_user: Annotated[User, Depends(require_permission("import_export.import"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[dict]:
    """Upload file for import."""
    # Validate file size/type if needed

    # Read file content
    content = await file.read()

    # Upload using FileService
    uploaded_file = await service.file_service.upload_file(
        file_content=content,
        filename=file.filename,
        entity_type="import_job",
        entity_id=None,  # Not linked to job yet
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        description="Import file",
    )

    return StandardResponse(
        data={
            "id": uploaded_file.id,
            "name": uploaded_file.name,
            "url": uploaded_file.storage_url,
            "storage_path": uploaded_file.storage_path,
        },
        message="File uploaded successfully",
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
    module: str | None = Query(default=None, description="Filter by module"),
    status: str | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ImportJobResponse]:
    """List import jobs."""
    skip = (page - 1) * page_size
    total = service.count_import_jobs(
        tenant_id=current_user.tenant_id,
        module=module,
        status=status,
    )

    jobs = service.repository.get_import_jobs(
        tenant_id=current_user.tenant_id,
        module=module,
        status=status,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ImportJobResponse.model_validate(j) for j in jobs],
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
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
    job_id: Annotated[UUID, Path(..., description="Import job ID")],
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[ImportJobResponse]:
    """Get a specific import job."""
    job = service.get_import_job(job_id, current_user.tenant_id)
    if not job:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="IMPORT_JOB_NOT_FOUND",
            message=f"Import job with ID {job_id} not found",
        )

    return StandardResponse(
        data=ImportJobResponse.model_validate(job),
        message="Import job retrieved successfully",
    )


@router.get(
    "/import/jobs/{job_id}/errors",
    response_model=StandardResponse[list[dict]],
    status_code=status.HTTP_200_OK,
    summary="Get import job errors",
    description="Get validation errors for a specific import job. Requires import_export.view permission.",
)
async def get_import_job_errors(
    job_id: Annotated[UUID, Path(..., description="Import job ID")],
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[list[dict]]:
    """Get import job errors."""
    errors = await service.get_import_job_errors(job_id, current_user.tenant_id)
    if errors is None:  # Job not found
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="IMPORT_JOB_NOT_FOUND",
            message=f"Import job with ID {job_id} not found",
        )

    return StandardResponse(
        data=errors,
        message="Import job errors retrieved successfully",
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
    module: str | None = Query(default=None, description="Filter by module"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ImportTemplateResponse]:
    """List import templates."""
    skip = (page - 1) * page_size
    total = service.count_import_templates(
        tenant_id=current_user.tenant_id,
        module=module,
    )

    templates = service.get_import_templates(
        tenant_id=current_user.tenant_id,
        module=module,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ImportTemplateResponse.model_validate(t) for t in templates],
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
        message="Import templates retrieved successfully",
    )


@router.get(
    "/import/templates/{template_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download import template",
    description="Download import template file (Excel). Requires import_export.view permission.",
)
async def download_import_template(
    template_id: Annotated[UUID, Path(..., description="Import template ID")],
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StreamingResponse:
    """Download import template file."""
    import io

    file_content = await service.generate_import_template_file(
        template_id, current_user.tenant_id
    )
    if not file_content:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="IMPORT_TEMPLATE_NOT_FOUND",
            message=f"Import template with ID {template_id} not found",
        )

    return StreamingResponse(
        io.BytesIO(file_content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=template_{template_id}.xlsx"
        },
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
    module: str | None = Query(default=None, description="Filter by module"),
    status: str | None = Query(default=None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[ExportJobResponse]:
    """List export jobs."""
    skip = (page - 1) * page_size
    total = service.count_export_jobs(
        tenant_id=current_user.tenant_id,
        module=module,
        status=status,
    )

    jobs = service.repository.get_export_jobs(
        tenant_id=current_user.tenant_id,
        module=module,
        status=status,
        skip=skip,
        limit=page_size,
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[ExportJobResponse.model_validate(j) for j in jobs],
        meta={
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        },
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
    job_id: Annotated[UUID, Path(..., description="Export job ID")],
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StandardResponse[ExportJobResponse]:
    """Get a specific export job."""
    job = service.get_export_job(job_id, current_user.tenant_id)
    if not job:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EXPORT_JOB_NOT_FOUND",
            message=f"Export job with ID {job_id} not found",
        )

    return StandardResponse(
        data=ExportJobResponse.model_validate(job),
        message="Export job retrieved successfully",
    )


@router.get(
    "/export/jobs/{job_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download export file",
    description="Download the generated export file. Requires import_export.view permission.",
)
async def download_export_file(
    job_id: Annotated[UUID, Path(..., description="Export job ID")],
    current_user: Annotated[User, Depends(require_permission("import_export.view"))],
    service: Annotated[ImportExportService, Depends(get_import_export_service)],
) -> StreamingResponse:
    """Download export file."""
    import io

    result = await service.get_export_job_file(job_id, current_user.tenant_id)
    if not result:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EXPORT_FILE_NOT_FOUND",
            message=f"Export file for job {job_id} not found",
        )

    content, filename = result

    # Determine media type based on extension
    media_type = "application/octet-stream"
    if filename.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif filename.endswith(".csv"):
        media_type = "text/csv"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
