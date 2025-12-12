"""Files router for file and document management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File as FastAPIFile, Path, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.files.service import FileService
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.file import (
    FilePermissionRequest,
    FilePermissionResponse,
    FileResponse,
    FileUpdate,
    FileVersionResponse,
)

router = APIRouter()


def get_file_service(
    db: Annotated[Session, Depends(get_db)],
) -> FileService:
    """Dependency to get FileService."""
    return FileService(db)


@router.post(
    "/upload",
    response_model=StandardResponse[FileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload file",
    description="Upload a new file. Requires files.manage permission.",
)
async def upload_file(
    file: UploadFile = FastAPIFile(..., description="File to upload"),
    entity_type: str | None = Query(None, description="Entity type (e.g., 'product', 'order')"),
    entity_id: UUID | None = Query(None, description="Entity ID"),
    description: str | None = Query(None, description="File description"),
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardResponse[FileResponse]:
    """Upload a new file."""
    # Read file content
    content = await file.read()

    uploaded_file = await service.upload_file(
        file_content=content,
        filename=file.filename or "unnamed",
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        description=description,
    )

    return StandardResponse(
        data=FileResponse.model_validate(uploaded_file),
        message="File uploaded successfully",
    )


@router.get(
    "/{file_id}",
    response_model=StandardResponse[FileResponse],
    status_code=status.HTTP_200_OK,
    summary="Get file information",
    description="Get file information by ID. Requires files.view permission.",
)
async def get_file_info(
    file_id: UUID = Path(..., description="File ID"),
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardResponse[FileResponse]:
    """Get file information."""
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file or not file.is_current:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    return StandardResponse(
        data=FileResponse.model_validate(file),
        message="File retrieved successfully",
    )


@router.get(
    "/{file_id}/download",
    summary="Download file",
    description="Download file content. Requires files.view permission.",
    responses={
        200: {"description": "File content", "content": {"application/octet-stream": {}}},
        404: {"description": "File not found"},
    },
)
async def download_file(
    file_id: UUID = Path(..., description="File ID"),
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
):
    """Download file content."""
    try:
        content, file = await service.download_file(file_id, current_user.tenant_id)

        return StreamingResponse(
            iter([content]),
            media_type=file.mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{file.original_name}"',
                "Content-Length": str(file.size),
            },
        )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )


@router.put(
    "/{file_id}",
    response_model=StandardResponse[FileResponse],
    status_code=status.HTTP_200_OK,
    summary="Update file",
    description="Update file information. Requires files.manage permission.",
)
async def update_file(
    file_id: UUID = Path(..., description="File ID"),
    file_data: FileUpdate = ...,
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardResponse[FileResponse]:
    """Update file information."""
    update_dict = file_data.model_dump(exclude_unset=True)
    file = service.repository.update(file_id, current_user.tenant_id, update_dict)

    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    return StandardResponse(
        data=FileResponse.model_validate(file),
        message="File updated successfully",
    )


@router.delete(
    "/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete file",
    description="Delete a file (soft delete). Requires files.manage permission.",
)
async def delete_file(
    file_id: UUID = Path(..., description="File ID"),
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> None:
    """Delete a file."""
    deleted = await service.delete_file(file_id, current_user.tenant_id, current_user.id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )


@router.get(
    "/{file_id}/versions",
    response_model=StandardListResponse[FileVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="List file versions",
    description="List all versions of a file. Requires files.view permission.",
)
async def list_file_versions(
    file_id: UUID = Path(..., description="File ID"),
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardListResponse[FileVersionResponse]:
    """List all versions of a file."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    versions = service.get_file_versions(file_id, current_user.tenant_id)

    return StandardListResponse(
        data=[FileVersionResponse.model_validate(v) for v in versions],
        total=len(versions),
        page=1,
        page_size=len(versions),
        total_pages=1,
        message="File versions retrieved successfully",
    )


@router.post(
    "/{file_id}/versions",
    response_model=StandardResponse[FileVersionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create file version",
    description="Create a new version of a file. Requires files.manage permission.",
)
async def create_file_version(
    file_id: UUID = Path(..., description="File ID"),
    file: UploadFile = FastAPIFile(..., description="New file version"),
    change_description: str | None = Query(None, description="Description of changes"),
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardResponse[FileVersionResponse]:
    """Create a new version of a file."""
    # Read file content
    content = await file.read()

    version = await service.create_file_version(
        file_id=file_id,
        file_content=content,
        filename=file.filename or "unnamed",
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        change_description=change_description,
    )

    return StandardResponse(
        data=FileVersionResponse.model_validate(version),
        message="File version created successfully",
    )


@router.get(
    "/{file_id}/versions/{version_id}/download",
    summary="Download file version",
    description="Download a specific file version. Requires files.view permission.",
)
async def download_file_version(
    file_id: UUID = Path(..., description="File ID"),
    version_id: UUID = Path(..., description="Version ID"),
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
):
    """Download a specific file version."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Get version
    version = service.repository.get_version_by_id(version_id, current_user.tenant_id)
    if not version or version.file_id != file_id:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_VERSION_NOT_FOUND",
            message=f"File version with ID {version_id} not found",
        )

    # Download from storage
    content = await service.storage_backend.download(version.storage_path)

    return StreamingResponse(
        iter([content]),
        media_type=version.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="v{version.version_number}_{file.original_name}"',
            "Content-Length": str(version.size),
        },
    )


@router.put(
    "/{file_id}/permissions",
    response_model=StandardListResponse[FilePermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Update file permissions",
    description="Update file permissions. Requires files.manage permission.",
)
async def update_file_permissions(
    file_id: UUID = Path(..., description="File ID"),
    permissions: list[FilePermissionRequest] = ...,
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardListResponse[FilePermissionResponse]:
    """Update file permissions."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Convert permissions to dicts
    permissions_data = [p.model_dump() for p in permissions]

    # Set permissions
    created_permissions = service.set_file_permissions(
        file_id, permissions_data, current_user.tenant_id
    )

    return StandardListResponse(
        data=[FilePermissionResponse.model_validate(p) for p in created_permissions],
        total=len(created_permissions),
        page=1,
        page_size=len(created_permissions),
        total_pages=1,
        message="File permissions updated successfully",
    )


@router.get(
    "",
    response_model=StandardListResponse[FileResponse],
    status_code=status.HTTP_200_OK,
    summary="List files",
    description="List all files for the current tenant. Requires files.view permission.",
)
async def list_files(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: UUID | None = Query(None, description="Filter by entity ID"),
) -> StandardListResponse[FileResponse]:
    """List all files."""
    if entity_type and entity_id:
        files = service.repository.get_by_entity(
            entity_type, entity_id, current_user.tenant_id
        )
        total = len(files)
    else:
        skip = (page - 1) * page_size
        files = service.repository.get_all(
            current_user.tenant_id, skip=skip, limit=page_size
        )
        total = len(files)  # TODO: Add count method to repository

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[FileResponse.model_validate(f) for f in files],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        message="Files retrieved successfully",
    )

