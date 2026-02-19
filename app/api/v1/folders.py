"""API endpoints for folder management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.core.files.folder_service import FolderService
from app.models.folder import Folder
from app.models.user import User
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse
from app.schemas.folder import (
    FolderContentResponse,
    FolderCreate,
    FolderPermissionRequest,
    FolderPermissionResponse,
    FolderResponse,
    FolderTreeItem,
    FolderUpdate,
    MoveItemsRequest,
)

router = APIRouter(tags=["folders"])


def get_folder_service(db: Annotated[Session, Depends(get_db)]) -> FolderService:
    """Get folder service instance."""
    return FolderService(db)


@router.post(
    "",
    response_model=StandardResponse[FolderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create folder",
    description="Create a new folder. Requires files.manage permission.",
)
async def create_folder(
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_data: FolderCreate,
) -> StandardResponse[FolderResponse]:
    """Create a new folder."""
    try:
        folder = await service.create_folder(
            name=folder_data.name,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            parent_id=folder_data.parent_id,
            description=folder_data.description,
            color=folder_data.color,
            icon=folder_data.icon,
            entity_type=folder_data.entity_type,
            entity_id=folder_data.entity_id,
            metadata=folder_data.metadata,
        )

        folder_response = FolderResponse.model_validate(folder)
        try:
            folder_response.path = folder.get_path()
        except Exception:
            # If parent not loaded, use folder name as path
            folder_response.path = f"/{folder.name}"
        try:
            folder_response.depth = folder.get_depth()
        except Exception:
            # If parent not loaded, assume depth 0
            folder_response.depth = 0

        return StandardResponse(
            data=folder_response,
            message="Folder created successfully",
        )
    except ValueError as e:
        raise APIException(
            code="FOLDER_CREATE_ERROR",
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get(
    "",
    response_model=StandardListResponse[FolderResponse],
    summary="List folders",
    description="List folders. Requires files.view permission.",
)
async def list_folders(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    parent_id: UUID | None = Query(default=None, description="Parent folder ID (null for root)"),
    entity_type: str | None = Query(default=None, description="Entity type filter"),
    entity_id: UUID | None = Query(default=None, description="Entity ID filter"),
) -> StandardListResponse[FolderResponse]:
    """List folders."""
    folders = await service.list_folders(
        tenant_id=current_user.tenant_id,
        parent_id=parent_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    folder_responses = []
    for folder in folders:
        folder_response = FolderResponse.model_validate(folder)
        try:
            folder_response.path = folder.get_path()
        except Exception:
            # If parent not loaded, use folder name as path
            folder_response.path = f"/{folder.name}"
        try:
            folder_response.depth = folder.get_depth()
        except Exception:
            # If parent not loaded, assume depth 0
            folder_response.depth = 0
        folder_responses.append(folder_response)

    return StandardListResponse(
        data=folder_responses,
        meta=PaginationMeta(
            total=len(folder_responses),
            page=1,
            page_size=len(folder_responses) or 1,
            total_pages=1 if len(folder_responses) == 0 else 1,
        ),
    )


@router.get(
    "/tree",
    response_model=StandardListResponse[FolderTreeItem],
    summary="Get folder tree",
    description="Get folder tree structure. Requires files.view permission.",
)
async def get_folder_tree(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    parent_id: UUID | None = Query(default=None, description="Parent folder ID (null for root)"),
    entity_type: str | None = Query(default=None, description="Entity type filter"),
    entity_id: UUID | None = Query(default=None, description="Entity ID filter"),
) -> StandardListResponse[FolderTreeItem]:
    """Get folder tree."""
    try:
        folders = await service.get_folder_tree(
            tenant_id=current_user.tenant_id,
            parent_id=parent_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting folder tree: {e}", exc_info=True)
        folders = []

    def build_tree_item(folder: Folder) -> FolderTreeItem:
        """Build tree item recursively."""
        # Get children - folder.children should be loaded by selectinload
        children = []
        try:
            if hasattr(folder, 'children'):
                children_list = list(folder.children) if folder.children else []
                children = [build_tree_item(child) for child in children_list]
        except Exception:
            # If children access fails, continue with empty children
            children = []

        # Get file count - use files relationship if available
        file_count = 0
        try:
            if hasattr(folder, 'files'):
                file_count = folder.files.count()
        except Exception:
            # If files relationship not available, default to 0
            file_count = 0

        # Build folder item - handle path and depth safely
        try:
            folder_item = FolderTreeItem.model_validate(folder)
            try:
                folder_item.path = folder.get_path()
            except Exception:
                folder_item.path = f"/{folder.name}"
            try:
                folder_item.depth = folder.get_depth()
            except Exception:
                folder_item.depth = 0
            folder_item.children = children
            folder_item.file_count = file_count
            return folder_item
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error building tree item for folder {folder.id}: {e}", exc_info=True)
            # Return minimal tree item
            folder_item = FolderTreeItem(
                id=folder.id,
                tenant_id=folder.tenant_id,
                name=folder.name,
                description=folder.description,
                color=folder.color,
                icon=folder.icon,
                parent_id=folder.parent_id,
                entity_type=folder.entity_type,
                entity_id=folder.entity_id,
                metadata=folder.folder_metadata,
                created_by=folder.created_by,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
                path=f"/{folder.name}",
                depth=0,
                children=[],
                file_count=0,
            )
            return folder_item

    tree_items = [build_tree_item(folder) for folder in folders] if folders else []

    return StandardListResponse(
        data=tree_items,
        meta=PaginationMeta(
            total=len(tree_items),
            page=1,
            page_size=len(tree_items) or 1,
            total_pages=1 if len(tree_items) == 0 else 1,
        ),
    )


@router.get(
    "/{folder_id}",
    response_model=StandardResponse[FolderResponse],
    summary="Get folder",
    description="Get a folder by ID. Requires files.view permission.",
)
async def get_folder(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_id: UUID,
) -> StandardResponse[FolderResponse]:
    """Get a folder by ID."""
    try:
        folder = await service.get_folder(folder_id, current_user.tenant_id)
        if not folder:
            raise APIException(
                code="FOLDER_NOT_FOUND",
                message="Folder not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        folder_response = FolderResponse.model_validate(folder)
        try:
            folder_response.path = folder.get_path()
        except Exception:
            # If parent not loaded, use folder name as path
            folder_response.path = f"/{folder.name}"
        try:
            folder_response.depth = folder.get_depth()
        except Exception:
            # If parent not loaded, assume depth 0
            folder_response.depth = 0

        return StandardResponse(
            data=folder_response,
            message="Folder retrieved successfully",
        )
    except APIException:
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting folder {folder_id}: {e}", exc_info=True)
        raise APIException(
            code="FOLDER_RETRIEVE_ERROR",
            message="An error occurred while retrieving the folder",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get(
    "/{folder_id}/content",
    response_model=StandardResponse[FolderContentResponse],
    summary="Get folder content",
    description="Get folder content (files and subfolders). Requires files.view permission.",
)
async def get_folder_content(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_id: UUID,
) -> StandardResponse[FolderContentResponse]:
    """Get folder content."""
    from app.core.files.service import FileService
    from app.schemas.file import FileResponse

    folder = await service.get_folder(folder_id, current_user.tenant_id)
    if not folder:
        raise APIException(
            code="FOLDER_NOT_FOUND",
            message="Folder not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Get subfolders
    subfolders = await service.list_folders(
        tenant_id=current_user.tenant_id,
        parent_id=folder_id,
    )

    # Get files in folder
    FileService(service.db, tenant_id=current_user.tenant_id)
    files_query = folder.files.filter_by(tenant_id=current_user.tenant_id, is_current=True)
    files = files_query.all()

    folder_response = FolderResponse.model_validate(folder)
    folder_response.path = folder.get_path()
    folder_response.depth = folder.get_depth()

    folder_responses = []
    for subfolder in subfolders:
        subfolder_response = FolderResponse.model_validate(subfolder)
        subfolder_response.path = subfolder.get_path()
        subfolder_response.depth = subfolder.get_depth()
        folder_responses.append(subfolder_response)

    file_responses = [FileResponse.model_validate(file) for file in files]

    content = FolderContentResponse(
        folder=folder_response,
        folders=folder_responses,
        files=file_responses,
        total_folders=len(folder_responses),
        total_files=len(file_responses),
    )

    return StandardResponse(
        data=content,
        message="Folder content retrieved successfully",
    )


@router.put(
    "/{folder_id}",
    response_model=StandardResponse[FolderResponse],
    summary="Update folder",
    description="Update a folder. Requires files.manage permission.",
)
async def update_folder(
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_id: UUID,
    folder_data: FolderUpdate,
) -> StandardResponse[FolderResponse]:
    """Update a folder."""
    try:
        folder = await service.update_folder(
            folder_id=folder_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            name=folder_data.name,
            description=folder_data.description,
            color=folder_data.color,
            icon=folder_data.icon,
            metadata=folder_data.metadata,
        )

        if not folder:
            raise APIException(
                code="FOLDER_NOT_FOUND",
                message="Folder not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        folder_response = FolderResponse.model_validate(folder)
        try:
            folder_response.path = folder.get_path()
        except Exception:
            # If parent not loaded, use folder name as path
            folder_response.path = f"/{folder.name}"
        try:
            folder_response.depth = folder.get_depth()
        except Exception:
            # If parent not loaded, assume depth 0
            folder_response.depth = 0

        return StandardResponse(
            data=folder_response,
            message="Folder updated successfully",
        )
    except ValueError as e:
        raise APIException(
            code="FOLDER_UPDATE_ERROR",
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.delete(
    "/{folder_id}",
    response_model=StandardResponse[dict],
    summary="Delete folder",
    description="Delete a folder. Requires files.manage permission.",
)
async def delete_folder(
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_id: UUID,
) -> StandardResponse[dict]:
    """Delete a folder."""
    try:
        deleted = await service.delete_folder(
            folder_id=folder_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
        )

        if not deleted:
            raise APIException(
                code="FOLDER_NOT_FOUND",
                message="Folder not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return StandardResponse(
            data={},
            message="Folder deleted successfully",
        )
    except APIException:
        raise
    except ValueError as e:
        raise APIException(
            code="FOLDER_DELETE_ERROR",
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting folder {folder_id}: {e}", exc_info=True)
        # Check if folder exists to determine if it's 404 or 500
        folder = await service.get_folder(folder_id, current_user.tenant_id)
        if not folder:
            raise APIException(
                code="FOLDER_NOT_FOUND",
                message="Folder not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        raise APIException(
            code="FOLDER_DELETE_ERROR",
            message="An error occurred while deleting the folder",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post(
    "/{folder_id}/move",
    response_model=StandardResponse[FolderResponse],
    summary="Move folder",
    description="Move a folder to a new parent. Requires files.manage permission.",
)
async def move_folder(
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_id: UUID,
    new_parent_id: UUID | None = Query(default=None, description="New parent folder ID (null for root)"),
) -> StandardResponse[FolderResponse]:
    """Move a folder."""
    try:
        folder = await service.move_folder(
            folder_id=folder_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            new_parent_id=new_parent_id,
        )

        if not folder:
            raise APIException(
                code="FOLDER_NOT_FOUND",
                message="Folder not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        folder_response = FolderResponse.model_validate(folder)
        try:
            folder_response.path = folder.get_path()
        except Exception:
            # If parent not loaded, use folder name as path
            folder_response.path = f"/{folder.name}"
        try:
            folder_response.depth = folder.get_depth()
        except Exception:
            # If parent not loaded, assume depth 0
            folder_response.depth = 0

        return StandardResponse(
            data=folder_response,
            message="Folder moved successfully",
        )
    except ValueError as e:
        raise APIException(
            code="FOLDER_MOVE_ERROR",
            message=str(e),
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.post(
    "/move-items",
    response_model=StandardResponse[dict],
    summary="Move files and folders",
    description="Move files and folders to a target folder. Requires files.manage permission.",
)
async def move_items(
    current_user: Annotated[User, Depends(require_permission("files.manage"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    move_data: MoveItemsRequest,
) -> StandardResponse[dict]:
    """Move files and folders to a target folder."""
    from app.core.files.service import FileService

    file_service = FileService(service.db, tenant_id=current_user.tenant_id)

    moved_files = []
    moved_folders = []

    # Move files
    for file_id in move_data.file_ids:
        # Update file's folder_id
        file = file_service.repository.get_by_id(file_id, current_user.tenant_id)
        if file:
            file.folder_id = move_data.target_folder_id
            service.db.commit()
            moved_files.append(str(file_id))

    # Move folders
    for folder_id in move_data.folder_ids:
        try:
            folder = await service.move_folder(
                folder_id=folder_id,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                new_parent_id=move_data.target_folder_id,
            )
            if folder:
                moved_folders.append(str(folder_id))
        except ValueError:
            # Skip if move fails (e.g., name conflict)
            pass

    return StandardResponse(
        data={
            "moved_files": moved_files,
            "moved_folders": moved_folders,
        },
        message=f"Moved {len(moved_files)} files and {len(moved_folders)} folders",
    )


@router.get(
    "/{folder_id}/path",
    response_model=StandardListResponse[FolderResponse],
    summary="Get folder path",
    description="Get folder path (breadcrumbs). Requires files.view permission.",
)
async def get_folder_path(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_id: UUID,
) -> StandardListResponse[FolderResponse]:
    """Get folder path (breadcrumbs)."""
    path = await service.get_folder_path(folder_id, current_user.tenant_id)

    path_responses = []
    for folder in path:
        folder_response = FolderResponse.model_validate(folder)
        try:
            folder_response.path = folder.get_path()
        except Exception:
            # If parent not loaded, use folder name as path
            folder_response.path = f"/{folder.name}"
        try:
            folder_response.depth = folder.get_depth()
        except Exception:
            # If parent not loaded, assume depth 0
            folder_response.depth = 0
        path_responses.append(folder_response)

    return StandardListResponse(
        data=path_responses,
        meta=PaginationMeta(
            total=len(path_responses),
            page=1,
            page_size=len(path_responses) or 1,
            total_pages=1 if len(path_responses) == 0 else 1,
        ),
    )


@router.get(
    "/search",
    response_model=StandardListResponse[FolderResponse],
    summary="Search folders",
    description="Search folders by name. Requires files.view permission.",
)
async def search_folders(
    current_user: Annotated[User, Depends(require_permission("files.view"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    query: str = Query(..., min_length=1, description="Search query"),
    entity_type: str | None = Query(default=None, description="Entity type filter"),
) -> StandardListResponse[FolderResponse]:
    """Search folders."""
    folders = await service.search_folders(
        tenant_id=current_user.tenant_id,
        query=query,
        entity_type=entity_type,
    )

    folder_responses = []
    for folder in folders:
        folder_response = FolderResponse.model_validate(folder)
        try:
            folder_response.path = folder.get_path()
        except Exception:
            # If parent not loaded, use folder name as path
            folder_response.path = f"/{folder.name}"
        try:
            folder_response.depth = folder.get_depth()
        except Exception:
            # If parent not loaded, assume depth 0
            folder_response.depth = 0
        folder_responses.append(folder_response)

    return StandardListResponse(
        data=folder_responses,
        meta=PaginationMeta(
            total=len(folder_responses),
            page=1,
            page_size=len(folder_responses) or 1,
            total_pages=1 if len(folder_responses) == 0 else 1,
        ),
    )


@router.get(
    "/{folder_id}/permissions",
    response_model=StandardListResponse[FolderPermissionResponse],
    summary="List folder permissions",
    description="List permissions for a folder. Requires folders.manage permission or folder ownership.",
)
async def get_folder_permissions(
    current_user: Annotated[User, Depends(require_permission("folders.manage"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    folder_id: UUID,
) -> StandardListResponse[FolderPermissionResponse]:
    """Get folder permissions."""
    # Verify folder exists
    folder = await service.get_folder(folder_id, current_user.tenant_id)
    if not folder:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FOLDER_NOT_FOUND",
            message=f"Folder with ID {folder_id} not found",
        )

    # Check if user has permission to view permissions (owner can always view)
    if folder.created_by != current_user.id:
        try:
            has_permission = service.check_folder_permissions(
                folder_id=folder_id,
                user_id=current_user.id,
                tenant_id=current_user.tenant_id,
                permission="edit",
            )
            if not has_permission:
                raise APIException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    code="FOLDER_ACCESS_DENIED",
                    message="You do not have permission to view permissions for this folder",
                )
        except FileNotFoundError:
            raise APIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="FOLDER_NOT_FOUND",
                message=f"Folder with ID {folder_id} not found",
            )

    # Get permissions
    permissions = service.get_folder_permissions(folder_id, current_user.tenant_id)

    return StandardListResponse(
        data=[FolderPermissionResponse.model_validate(p) for p in permissions],
        meta=PaginationMeta(
            total=len(permissions),
            page=1,
            page_size=len(permissions) or 1,
            total_pages=1 if len(permissions) == 0 else 1,
        ),
    )


@router.put(
    "/{folder_id}/permissions",
    response_model=StandardListResponse[FolderPermissionResponse],
    status_code=status.HTTP_200_OK,
    summary="Update folder permissions",
    description="Update folder permissions. Requires folders.manage permission or folder ownership.",
)
async def update_folder_permissions(
    folder_id: Annotated[UUID, Path(..., description="Folder ID")],
    current_user: Annotated[User, Depends(require_permission("folders.manage"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
    permissions: list[FolderPermissionRequest],
) -> StandardListResponse[FolderPermissionResponse]:
    """Update folder permissions."""
    # Verify folder exists
    folder = await service.get_folder(folder_id, current_user.tenant_id)
    if not folder:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FOLDER_NOT_FOUND",
            message=f"Folder with ID {folder_id} not found",
        )

    # Check if user has permission to edit this specific folder (owner can always change permissions)
    # Owner has full access, otherwise check folders.manage_users permission
    if folder.created_by != current_user.id:
        # Check module-level permission
        from app.core.auth.dependencies import check_permission
        if not check_permission(current_user, "folders.manage_users"):
            raise APIException(
                status_code=status.HTTP_403_FORBIDDEN,
                code="FOLDER_PERMISSION_DENIED",
                message="You do not have permission to manage permissions for this folder. Requires folders.manage_users permission or folder ownership.",
            )

    # Convert permissions to dicts
    permissions_data = [p.model_dump() for p in permissions]

    # Set permissions (validates target_id exists and belongs to tenant)
    try:
        created_permissions = service.set_folder_permissions(
            folder_id=folder_id,
            permissions=permissions_data,
            tenant_id=current_user.tenant_id,
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_PERMISSION_TARGET",
            message=str(e),
        )

    return StandardListResponse(
        data=[FolderPermissionResponse.model_validate(p) for p in created_permissions],
        meta=PaginationMeta(
            total=len(created_permissions),
            page=1,
            page_size=len(created_permissions) or 1,
            total_pages=1 if len(created_permissions) == 0 else 1,
        ),
    )


@router.get(
    "/{folder_id}/permissions/check",
    response_model=StandardResponse[dict],
    summary="Check folder permissions",
    description="Check current user's permissions for a folder. Requires folders.view permission.",
)
async def check_folder_permissions_endpoint(
    folder_id: Annotated[UUID, Path(..., description="Folder ID")],
    current_user: Annotated[User, Depends(require_permission("folders.view"))],
    service: Annotated[FolderService, Depends(get_folder_service)],
) -> StandardResponse[dict]:
    """Check current user's permissions for a folder."""
    # Verify folder exists
    folder = await service.get_folder(folder_id, current_user.tenant_id)
    if not folder:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="FOLDER_NOT_FOUND",
            message=f"Folder with ID {folder_id} not found",
        )

    # Check if user is owner
    is_owner = folder.created_by == current_user.id

    # Check permissions
    can_view = is_owner or service.check_folder_permissions(
        folder_id, current_user.id, current_user.tenant_id, "view"
    )
    can_create_files = is_owner or service.check_folder_permissions(
        folder_id, current_user.id, current_user.tenant_id, "create_files"
    )
    can_create_folders = is_owner or service.check_folder_permissions(
        folder_id, current_user.id, current_user.tenant_id, "create_folders"
    )
    can_edit = is_owner or service.check_folder_permissions(
        folder_id, current_user.id, current_user.tenant_id, "edit"
    )
    can_delete = is_owner or service.check_folder_permissions(
        folder_id, current_user.id, current_user.tenant_id, "delete"
    )

    return StandardResponse(
        data={
            "can_view": can_view,
            "can_create_files": can_create_files,
            "can_create_folders": can_create_folders,
            "can_edit": can_edit,
            "can_delete": can_delete,
            "is_owner": is_owner,
        },
        message="Folder permissions checked successfully",
    )

