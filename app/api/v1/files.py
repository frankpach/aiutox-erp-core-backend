"""Files router for file and document management."""

import logging
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
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.file import (
    FilePermissionRequest,
    FilePermissionResponse,
    FileResponse,
    FileUpdate,
    FileVersionResponse,
)
from app.schemas.tag import TagResponse

router = APIRouter()

logger = logging.getLogger(__name__)


def get_file_service(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
) -> FileService:
    """Dependency to get FileService."""
    return FileService(db, tenant_id=current_user.tenant_id)


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

    # Transform uploaded_by_user relationship to dict format before validation
    uploaded_by_user_dict = None
    if file.uploaded_by_user:
        uploaded_by_user_dict = {
            "id": str(file.uploaded_by_user.id),
            "email": file.uploaded_by_user.email,
            "full_name": file.uploaded_by_user.full_name or f"{file.uploaded_by_user.first_name or ''} {file.uploaded_by_user.last_name or ''}".strip() or file.uploaded_by_user.email,
        }

    # Create response dict with transformed user data
    # Get tags for the file
    file_tags = []
    try:
        tags = service.get_file_tags(file.id, current_user.tenant_id)
        file_tags = [TagResponse.model_validate(tag) for tag in tags]
    except FileNotFoundError:
        pass  # File not found, skip tags
    except Exception as e:
        logger.warning(f"Error getting tags for file {file.id}: {e}")

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
        "folder_id": getattr(file, "folder_id", None),
        "uploaded_by": file.uploaded_by,
        "uploaded_by_user": uploaded_by_user_dict,
        "tags": file_tags or [],
        "deleted_at": getattr(file, "deleted_at", None),
        "entity_type": file.entity_type,
        "entity_id": file.entity_id,
        "description": file.description,
        "metadata": getattr(file, "file_metadata", None),
        "created_at": file.created_at,
        "updated_at": file.updated_at,
    }

    return StandardResponse(
        data=FileResponse.model_validate(file_dict),
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


@router.post(
    "/{file_id}/restore",
    response_model=StandardResponse[FileResponse],
    summary="Restore deleted file",
    description="Restore a soft-deleted file. Requires files.manage permission.",
)
async def restore_file(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardResponse[FileResponse]:
    """Restore a soft-deleted file."""
    restored = await service.restore_file(
        file_id, current_user.tenant_id, current_user.id
    )
    if not restored:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found or already restored",
        )

    # Get file info (allow deleted files for restore endpoint)
    file = service.repository.get_by_id(file_id, current_user.tenant_id, current_only=False)
    if not file:
        # Try to get the file even if it's deleted
        from app.models.file import File
        file = (
            service.db.query(File)
            .filter(File.id == file_id, File.tenant_id == current_user.tenant_id)
            .first()
        )
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Convert to response format
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
        "entity_type": file.entity_type,
        "entity_id": file.entity_id,
        "folder_id": file.folder_id,
        "description": file.description,
        "metadata": file.file_metadata,
        "version_number": file.version_number,
        "is_current": file.is_current,
        "deleted_at": file.deleted_at,
        "uploaded_by": file.uploaded_by,
        "created_at": file.created_at,
        "updated_at": file.updated_at,
    }

    # Load user relationship if available
    if file.uploaded_by_user:
        file_dict["uploaded_by_user"] = {
            "id": file.uploaded_by_user.id,
            "email": file.uploaded_by_user.email,
            "full_name": file.uploaded_by_user.full_name,
        }
    else:
        file_dict["uploaded_by_user"] = None

    return StandardResponse(data=FileResponse.model_validate(file_dict))


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

    try:
        versions = service.get_file_versions(file_id, current_user.tenant_id)

        # If no versions exist, this is a problem - every file should have at least v1
        # However, we'll return empty list gracefully and log a warning
        if not versions:
            logger.warning(
                f"File {file_id} has no versions in file_versions table. "
                f"File version_number is {file.version_number}. "
                f"This may indicate a data inconsistency."
            )
            return StandardListResponse(
                data=[],
                meta=PaginationMeta(
                    total=0,
                    page=1,
                    page_size=1,  # Must be at least 1 per PaginationMeta constraint
                    total_pages=1,
                ),
                message="No versions found for this file",
            )

        # Convert FileVersion objects to dict format for validation
        versions_data = []
        for v in versions:
            try:
                version_dict = {
                    "id": v.id,
                    "file_id": v.file_id,
                    "version_number": v.version_number,
                    "storage_path": v.storage_path,
                    "storage_backend": v.storage_backend,
                    "size": v.size,
                    "mime_type": v.mime_type,
                    "change_description": v.change_description,
                    "created_by": v.created_by,
                    "created_at": v.created_at,
                }
                versions_data.append(FileVersionResponse.model_validate(version_dict))
            except Exception as e:
                logger.error(f"Error converting FileVersion {v.id} to response: {e}", exc_info=True)
                # Skip this version but continue with others
                continue

        # Ensure page_size is at least 1 (required by PaginationMeta constraint)
        page_size = max(1, len(versions_data))
        return StandardListResponse(
            data=versions_data,
            meta=PaginationMeta(
                total=len(versions_data),
                page=1,
                page_size=page_size,
                total_pages=1 if len(versions_data) == 0 else 1,
            ),
            message="File versions retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error retrieving file versions for file {file_id}: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="VERSIONS_RETRIEVAL_FAILED",
            message=f"Failed to retrieve file versions: {str(e)}",
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


@router.post(
    "/{file_id}/versions/{version_id}/restore",
    response_model=StandardResponse[FileVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="Restore file version",
    description="Restore a specific file version by creating a new version with its content. Requires files.manage permission and specific file edit permission or ownership.",
)
async def restore_file_version(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    version_id: Annotated[UUID, Path(..., description="Version ID to restore")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
    change_description: str | None = Query(
        default=None, description="Description of restoration (optional)"
    ),
) -> StandardResponse[FileVersionResponse]:
    """Restore a file version by creating a new version with its content."""
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
                message="You do not have permission to restore versions of this file",
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

    # Download version content
    version_content = await service.storage_backend.download(version.storage_path)

    # Create new version with restored content
    restored_version = await service.create_file_version(
        file_id=file_id,
        file_content=version_content,
        filename=file.original_name,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        change_description=change_description or f"Restored from version {version.version_number}",
    )

    return StandardResponse(
        data=FileVersionResponse.model_validate(restored_version),
        message=f"File version {version.version_number} restored successfully",
    )


@router.get(
    "/{file_id}/permissions",
    response_model=StandardListResponse[FilePermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get file permissions",
    description="Get all permissions for a file. Requires files.view permission and specific file view permission or ownership.",
)
async def get_file_permissions(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardListResponse[FilePermissionResponse]:
    """Get file permissions."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Check if user has permission to view this specific file (owner can always view permissions)
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

    # Get permissions
    permissions = service.repository.get_permissions(file_id, current_user.tenant_id)

    return StandardListResponse(
        data=[FilePermissionResponse.model_validate(p) for p in permissions],
        total=len(permissions),
        page=1,
        page_size=len(permissions),
        total_pages=1,
        message="File permissions retrieved successfully",
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


@router.post(
    "/{file_id}/tags",
    response_model=StandardListResponse[TagResponse],
    status_code=status.HTTP_200_OK,
    summary="Add tags to file",
    description="Add tags to a file. Requires files.manage permission and specific file edit permission or ownership.",
)
async def add_tags_to_file(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
    tag_ids: list[UUID] = Query(..., description="List of tag IDs to add"),
) -> StandardListResponse[TagResponse]:
    """Add tags to a file."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

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
                message="You do not have permission to add tags to this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Add tags
    try:
        added_tags = service.add_tags_to_file(
            file_id=file_id,
            tag_ids=tag_ids,
            tenant_id=current_user.tenant_id,
        )
    except FileNotFoundError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_OR_TAG_NOT_FOUND",
            message=str(e),
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="TAG_OPERATION_FAILED",
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Error adding tags to file {file_id}: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="TAG_OPERATION_FAILED",
            message=f"Failed to add tags to file: {str(e)}",
        )

    tags_list = [TagResponse.model_validate(tag) for tag in added_tags]
    return StandardListResponse(
        data=tags_list,
        meta=PaginationMeta(
            total=len(tags_list),
            page=1,
            page_size=max(len(tags_list), 1),  # page_size must be >= 1
            total_pages=1,
        ),
    )


@router.delete(
    "/{file_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tag from file",
    description="Remove a tag from a file. Requires files.manage permission and specific file edit permission or ownership.",
)
async def remove_tag_from_file(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    tag_id: Annotated[UUID, Path(..., description="Tag ID")],
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> None:
    """Remove a tag from a file."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

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
                message="You do not have permission to remove tags from this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Remove tag
    try:
        removed = service.remove_tag_from_file(
            file_id=file_id,
            tag_id=tag_id,
            tenant_id=current_user.tenant_id,
        )
    except FileNotFoundError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_OR_TAG_NOT_FOUND",
            message=str(e),
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="TAG_OPERATION_FAILED",
            message=str(e),
        )
    except Exception as e:
        logger.error(f"Error removing tag {tag_id} from file {file_id}: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="TAG_OPERATION_FAILED",
            message=f"Failed to remove tag from file: {str(e)}",
        )

    if not removed:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="TAG_NOT_FOUND",
            message=f"Tag {tag_id} not found on file {file_id}",
        )


@router.get(
    "/{file_id}/tags",
    response_model=StandardListResponse[TagResponse],
    status_code=status.HTTP_200_OK,
    summary="Get file tags",
    description="Get all tags for a file. Requires files.view permission and specific file view permission.",
)
async def get_file_tags(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> StandardListResponse[TagResponse]:
    """Get all tags for a file."""
    # Verify file exists
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
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
                message="You do not have permission to view tags for this file",
            )
    except FileNotFoundError:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Get tags
    try:
        tags = service.get_file_tags(
            file_id=file_id,
            tenant_id=current_user.tenant_id,
        )
    except FileNotFoundError as e:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=str(e) if str(e) else f"File with ID {file_id} not found",
        )
    except Exception as e:
        logger.error(f"Error getting tags for file {file_id}: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="TAG_RETRIEVAL_FAILED",
            message=f"Failed to retrieve file tags: {str(e)}",
        )

    tags_list = [TagResponse.model_validate(tag) for tag in tags]
    return StandardListResponse(
        data=tags_list,
        meta=PaginationMeta(
            total=len(tags_list),
            page=1,
            page_size=max(len(tags_list), 1),  # page_size must be >= 1
            total_pages=1,
        ),
    )


@router.get(
    "/{file_id}/content",
    status_code=status.HTTP_200_OK,
    summary="Get file content",
    description="Get raw content of a text file. Only works for text files (text/*, application/json, etc.). Requires files.view permission and specific file view permission.",
    responses={
        200: {
            "description": "File content",
            "content": {
                "text/plain": {},
                "application/json": {},
            },
        },
    },
)
async def get_file_content(
    file_id: Annotated[UUID, Path(..., description="File ID")],
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FileService, Depends(get_file_service)],
) -> Response:
    """Get raw content of a text file."""
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

    # Get file
    file = service.repository.get_by_id(file_id, current_user.tenant_id)
    if not file or not file.is_current:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FILE_NOT_FOUND",
            message=f"File with ID {file_id} not found",
        )

    # Only allow text files
    text_mime_types = [
        "text/",
        "application/json",
        "application/xml",
        "application/yaml",
        "application/x-yaml",
    ]
    if not any(file.mime_type.startswith(prefix) for prefix in text_mime_types):
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_FILE_TYPE",
            message="Content endpoint only supports text files",
        )

    # Limit file size for preview (5MB)
    MAX_PREVIEW_SIZE = 5 * 1024 * 1024
    if file.size > MAX_PREVIEW_SIZE:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="FILE_TOO_LARGE",
            message=f"File is too large for preview (max {MAX_PREVIEW_SIZE} bytes)",
        )

    try:
        # Download file content
        content, _ = await service.download_file(file_id, current_user.tenant_id)

        # Determine content type
        content_type = file.mime_type
        if file.mime_type == "application/json":
            content_type = "application/json"
        elif file.mime_type.startswith("text/"):
            content_type = file.mime_type

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{file.original_name}"',
            },
        )
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting file content: {e}", exc_info=True)
        raise APIException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="FILE_CONTENT_ERROR",
            message=f"Failed to retrieve file content: {str(e)}",
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
    tags: str | None = Query(default=None, description="Comma-separated list of tag IDs to filter by (files must have ALL tags)"),
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
        # Get total count using service method
        total = service.count_files_by_entity_user_can_view(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )
        # Get files by entity and filter by permissions
        skip = (page - 1) * page_size
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
        # Apply pagination
        files = files[skip : skip + page_size]
    else:
        # Parse tag IDs from comma-separated string
        tag_ids: list[UUID] | None = None
        if tags:
            try:
                tag_ids = [UUID(tag_id.strip()) for tag_id in tags.split(",") if tag_id.strip()]
            except ValueError as e:
                raise APIException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    code="INVALID_TAG_IDS",
                    message=f"Invalid tag ID format: {str(e)}",
                )

        # Get files filtered by permissions
        try:
            skip = (page - 1) * page_size
            files = service.get_files_user_can_view(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                skip=skip,
                limit=page_size,
                folder_id=folder_id,
                tag_ids=tag_ids,
            )
            total = service.count_files_user_can_view(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                folder_id=folder_id,
                tag_ids=tag_ids,
            )
        except Exception as e:
            logger.error(f"Error getting files for user {current_user.id}: {e}", exc_info=True)
            raise APIException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code="FILES_LIST_ERROR",
                message=f"Error retrieving files: {str(e)}",
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

        # Get tags for the file
        file_tags = []
        try:
            tags = service.get_file_tags(file.id, current_user.tenant_id)
            file_tags = [TagResponse.model_validate(tag) for tag in tags]
        except FileNotFoundError:
            pass  # File not found, skip tags
        except Exception as e:
            logger.warning(f"Error getting tags for file {file.id}: {e}")

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
            "tags": file_tags or [],
            "deleted_at": file.deleted_at,
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

