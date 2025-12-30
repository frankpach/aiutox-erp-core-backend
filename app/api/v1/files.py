"""Files router for file and document management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File as FastAPIFile, Path, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
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
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
    file: UploadFile = FastAPIFile(..., description="File to upload"),
    entity_type: str | None = Query(default=None, description="Entity type (e.g., 'product', 'order')"),
    entity_id: UUID | None = Query(default=None, description="Entity ID"),
    folder_id: UUID | None = Query(default=None, description="Folder ID (null for root)"),
    description: str | None = Query(default=None, description="File description"),
    permissions: str | None = Query(default=None, description="JSON array of permissions to assign"),
) -> StandardResponse[FileResponse]:
    """Upload a new file."""
    import json

    # Validate tenant_id
    if not current_user.tenant_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_TENANT",
            message="User must have a tenant assigned. Please contact administrator.",
        )

    # Read file content
    content = await file.read()

    # Parse permissions if provided
    permissions_data = None
    if permissions:
        try:
            permissions_data = json.loads(permissions)
            # Validate permissions format
            if not isinstance(permissions_data, list):
                raise ValueError("Permissions must be a JSON array")
            for perm in permissions_data:
                if not all(k in perm for k in ["target_type", "target_id"]):
                    raise ValueError("Each permission must have target_type and target_id")
        except json.JSONDecodeError:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid JSON format for permissions",
            )

    # Reload file with user relationship for response
    from sqlalchemy.orm import joinedload
    import logging

    logger = logging.getLogger(__name__)

    try:
        uploaded_file = await service.upload_file(
            file_content=content,
            filename=file.filename or "unnamed",
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            description=description,
            folder_id=folder_id,
            permissions=permissions_data,
        )
        logger.info(f"File uploaded successfully: {uploaded_file.id}")
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="FILE_UPLOAD_FAILED",
            message=f"Failed to upload file: {str(e)}",
        )

    # Reload with user info (non-blocking - use uploaded_file if reload fails)
    from app.models.file import File
    try:
        file_with_user = (
            service.db.query(File)
            .options(joinedload(File.uploaded_by_user))
            .filter(File.id == uploaded_file.id)
            .first()
        )
    except Exception as e:
        logger.warning(f"Failed to reload file with user info: {e}, using uploaded_file directly")
        file_with_user = None

    try:
        # Transform uploaded_by_user relationship to dict format before validation
        uploaded_by_user_dict = None
        file_to_validate = file_with_user or uploaded_file

        if file_to_validate and hasattr(file_to_validate, 'uploaded_by_user') and file_to_validate.uploaded_by_user:
            uploaded_by_user_dict = {
                "id": str(file_to_validate.uploaded_by_user.id),
                "email": file_to_validate.uploaded_by_user.email,
                "full_name": file_to_validate.uploaded_by_user.full_name or f"{file_to_validate.uploaded_by_user.first_name or ''} {file_to_validate.uploaded_by_user.last_name or ''}".strip() or file_to_validate.uploaded_by_user.email,
            }

        # Create response dict with transformed user data (similar to list_files)
        file_dict = {
            "id": file_to_validate.id,
            "tenant_id": file_to_validate.tenant_id,
            "name": file_to_validate.name,
            "original_name": file_to_validate.original_name,
            "mime_type": file_to_validate.mime_type,
            "size": file_to_validate.size,
            "extension": file_to_validate.extension,
            "storage_backend": file_to_validate.storage_backend,
            "storage_path": file_to_validate.storage_path,
            "storage_url": file_to_validate.storage_url,
            "version_number": file_to_validate.version_number,
            "is_current": file_to_validate.is_current,
            "folder_id": getattr(file_to_validate, "folder_id", None),
            "uploaded_by": file_to_validate.uploaded_by,
            "uploaded_by_user": uploaded_by_user_dict,
            "entity_type": file_to_validate.entity_type,
            "entity_id": file_to_validate.entity_id,
            "description": file_to_validate.description,
            "metadata": getattr(file_to_validate, "file_metadata", None),
            "created_at": file_to_validate.created_at,
            "updated_at": file_to_validate.updated_at,
        }

        file_response = FileResponse.model_validate(file_dict)
    except Exception as e:
        logger.error(f"Error creating file response: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="FILE_RESPONSE_FAILED",
            message=f"Failed to create file response: {str(e)}",
        )

    return StandardResponse(
        data=file_response,
        message="File uploaded successfully",
    )


@router.get(
    "/{file_id}",
    response_model=StandardResponse[FileResponse],
    status_code=status.HTTP_200_OK,
    summary="Get file information",
    description="Get file information by ID. Requires files.view permission and specific file view permission.",
)
async def get_file_info(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardResponse[FileResponse]:
    """Get file information."""
    # Validate tenant_id
    if not current_user.tenant_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_TENANT",
            message="User must have a tenant assigned. Please contact administrator.",
        )

    # Check if user has permission to view this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="view",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to view this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file or not file.is_current:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    return StandardResponse(
        data=FileResponse.model_validate(file),
        message="File retrieved successfully",
    )


@router.get(
    "/{file_id}/download",
    summary="Download file",
    description="Download file content. Requires files.view permission and specific file download permission.",
    responses={
        200: {"description": "File content", "content": {"application/octet-stream": {}}},
        403: {"description": "Access denied"},
        404: {"description": "File not found"},
    },
)
async def download_file(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
):
    """Download file content."""
    # Validate tenant_id
    if not current_user.tenant_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_TENANT",
            message="User must have a tenant assigned. Please contact administrator.",
        )

    # Check if user has permission to download this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="download",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to download this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

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
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )


@router.get(
    "/{file_id}/preview",
    summary="Get file preview/thumbnail",
    description="Get a preview or thumbnail of an image file. Requires files.view permission and specific file view permission.",
    responses={
        200: {"description": "Image preview", "content": {"image/jpeg": {}}},
        403: {"description": "Access denied"},
        404: {"description": "File not found"},
        400: {"description": "File is not an image"},
    },
)
async def get_file_preview(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
    width: int = Query(default=200, ge=1, le=2000, description="Preview width in pixels"),
    height: int = Query(default=200, ge=1, le=2000, description="Preview height in pixels"),
    quality: int = Query(default=80, ge=1, le=100, description="JPEG quality (1-100)"),
) -> Response:
    """Get file preview/thumbnail."""
    # Check if user has permission to view this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="view",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to view this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    try:
        # Generate thumbnail
        preview_bytes = await service.generate_thumbnail(
            file_id=file_id,
            tenant_id=current_user.tenant_id,
            width=width,
            height=height,
            quality=quality,
        )

        return Response(
            content=preview_bytes,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(len(preview_bytes)),
            },
        )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="FILE_NOT_IMAGE",
            message=str(e),
        )


@router.put(
    "/{file_id}",
    response_model=StandardResponse[FileResponse],
    status_code=status.HTTP_200_OK,
    summary="Update file",
    description="Update file information. Requires files.manage permission and specific file edit permission or ownership.",
)
async def update_file(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
    file_data: FileUpdate,
) -> StandardResponse[FileResponse]:
    """Update file information."""
    # Check if user has permission to edit this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="edit",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to edit this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    update_dict = file_data.model_dump(exclude_unset=True)
    file = service.repository.update(file_id, current_user.tenant_id, update_dict)

    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
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
    description="Delete a file (soft delete). Requires files.manage permission and specific file delete permission or ownership.",
)
async def delete_file(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> None:
    """Delete a file."""
    # Check if user has permission to delete this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="delete",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to delete this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    deleted = await service.delete_file(file_id, current_user.tenant_id, current_user.id)
    if not deleted:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )


@router.get(
    "/{file_id}/versions",
    response_model=StandardListResponse[FileVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="List file versions",
    description="List all versions of a file. Requires files.view permission and specific file view permission.",
)
async def list_file_versions(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardListResponse[FileVersionResponse]:
    """List all versions of a file."""
    # Check if user has permission to view this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="view",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to view this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
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
    description="Create a new version of a file. Requires files.manage permission and specific file edit permission or ownership.",
)
async def create_file_version(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
    file: UploadFile = FastAPIFile(..., description="New file version"),
    change_description: str | None = Query(default=None, description="Description of changes"),
) -> StandardResponse[FileVersionResponse]:
    """Create a new version of a file."""
    # Check if user has permission to edit this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="edit",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to create versions of this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

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
    description="Download a specific file version. Requires files.view permission and specific file download permission.",
)
async def download_file_version(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    version_id: Annotated[UUID, Path(..., description="Version ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
):
    """Download a specific file version."""
    # Check if user has permission to download this specific file
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="download",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to download this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Get version
    version = service.repository.get_version_by_id(version_id, current_user.tenant_id)
    if not version or version.file_id != file_id:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_VERSION_NOT_FOUND",
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
    description="Update file permissions. Requires files.manage permission and specific file edit permission or ownership.",
)
async def update_file_permissions(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
    permissions: list[FilePermissionRequest],
) -> StandardListResponse[FilePermissionResponse]:
    """Update file permissions."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Check if user has permission to edit this specific file (owner can always change permissions)
    try:
        has_permission = service.check_permissions(
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            permission="edit",
        )
        if not has_permission:
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FILE_ACCESS_DENIED",
                message="You do not have permission to change permissions for this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
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
    description="List files that the user can view. Requires files.view permission and filters by specific file permissions.",
)
async def list_files(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
    entity_type: str | None = Query(default=None, description="Filter by entity type"),
    entity_id: UUID | None = Query(default=None, description="Filter by entity ID"),
    folder_id: UUID | None = Query(default=None, description="Filter by folder ID (null for root)"),
) -> StandardListResponse[FileResponse]:
    """List files that the user can view."""
    # Validate tenant_id
    if not current_user.tenant_id:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_TENANT",
            message="User must have a tenant assigned. Please contact administrator.",
        )

    if entity_type and entity_id:
        # Get files by entity and filter by permissions
        all_files = service.repository.get_by_entity(
            entity_type, entity_id, current_user.tenant_id
        )
        # Filter files by permissions
        files = []
        for file in all_files:
            try:
                if service.check_permissions(
                    file.id, current_user.id, current_user.tenant_id, "view"
                ):
                    files.append(file)
            except FileNotFoundError:
                continue
        total = len(files)
    else:
        # Get files filtered by permissions
        skip = (page - 1) * page_size
        files = service.get_files_user_can_view(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            skip=skip,
            limit=page_size,
            folder_id=folder_id,
        )
        total = service.count_files_user_can_view(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            folder_id=folder_id,
        )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Convert files to response format, transforming uploaded_by_user relationship to dict
    file_responses = []
    for file in files:
        # Transform uploaded_by_user relationship to dict format
        uploaded_by_user_dict = None
        if file.uploaded_by_user:
            uploaded_by_user_dict = {
                "id": str(file.uploaded_by_user.id),
                "email": file.uploaded_by_user.email,
                "full_name": file.uploaded_by_user.full_name or f"{file.uploaded_by_user.first_name or ''} {file.uploaded_by_user.last_name or ''}".strip() or file.uploaded_by_user.email,
            }

        # Create response dict with transformed user data
        file_dict = {
            "id": file.id,
            "tenant_id": file.tenant_id,
            "name": file.name,
            "original_name": file.original_name,
            "mime_type": file.mime_type,
            "size": file.size,
            "extension": file.extension,
            "storage_backend": file.storage_backend,
            "storage_path": file.storage_path,
            "storage_url": file.storage_url,
            "version_number": file.version_number,
            "is_current": file.is_current,
            "folder_id": file.folder_id,
            "uploaded_by": file.uploaded_by,
            "uploaded_by_user": uploaded_by_user_dict,
            "entity_type": file.entity_type,
            "entity_id": file.entity_id,
            "description": file.description,
            "metadata": getattr(file, "file_metadata", None),
            "created_at": file.created_at,
            "updated_at": file.updated_at,
        }
        file_responses.append(FileResponse.model_validate(file_dict))

    return StandardListResponse(
        data=file_responses,
        meta={
            "total": total,
            "page": page,
            "page_size": max(page_size, 1) if total == 0 else page_size,  # Minimum page_size is 1
            "total_pages": total_pages,
        },
    )

