"""API endpoints for folder management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.db.deps import get_db
from app.core.files.folder_service import FolderService
from app.core.auth.dependencies import require_permission
from app.core.exceptions import APIException
from app.models.user import User
from app.schemas.common import StandardListResponse, StandardResponse
from app.schemas.folder import (
    FolderCreate,
    FolderResponse,
    FolderTreeItem,
    FolderContentResponse,
    FolderUpdate,
    MoveItemsRequest,
)

router = APIRouter(prefix="/folders", tags=["folders"])


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
        folder_response.path = folder.get_path()
        folder_response.depth = folder.get_depth()

        return StandardResponse(
            data=folder_response,
            message="Folder created successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
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
        folder_response.path = folder.get_path()
        folder_response.depth = folder.get_depth()
        folder_responses.append(folder_response)

    return StandardListResponse(
        data=folder_responses,
        message="Folders retrieved successfully",
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
    folders = await service.get_folder_tree(
        tenant_id=current_user.tenant_id,
        parent_id=parent_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )

    def build_tree_item(folder: Folder) -> FolderTreeItem:
        """Build tree item recursively."""
        children = [build_tree_item(child) for child in folder.children]
        file_count = folder.files.count()

        folder_item = FolderTreeItem.model_validate(folder)
        folder_item.path = folder.get_path()
        folder_item.depth = folder.get_depth()
        folder_item.children = children
        folder_item.file_count = file_count
        return folder_item

    tree_items = [build_tree_item(folder) for folder in folders]

    return StandardListResponse(
        data=tree_items,
        message="Folder tree retrieved successfully",
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
    folder = await service.get_folder(folder_id, current_user.tenant_id)
    if not folder:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Folder not found",
        )

    folder_response = FolderResponse.model_validate(folder)
    folder_response.path = folder.get_path()
    folder_response.depth = folder.get_depth()

    return StandardResponse(
        data=folder_response,
        message="Folder retrieved successfully",
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
            status_code=status.HTTP_404_NOT_FOUND,
            message="Folder not found",
        )

    # Get subfolders
    subfolders = await service.list_folders(
        tenant_id=current_user.tenant_id,
        parent_id=folder_id,
    )

    # Get files in folder
    file_service = FileService(service.db)
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
                status_code=status.HTTP_404_NOT_FOUND,
                message="Folder not found",
            )

        folder_response = FolderResponse.model_validate(folder)
        folder_response.path = folder.get_path()
        folder_response.depth = folder.get_depth()

        return StandardResponse(
            data=folder_response,
            message="Folder updated successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
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
                status_code=status.HTTP_404_NOT_FOUND,
                message="Folder not found",
            )

        return StandardResponse(
            data={},
            message="Folder deleted successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
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
                status_code=status.HTTP_404_NOT_FOUND,
                message="Folder not found",
            )

        folder_response = FolderResponse.model_validate(folder)
        folder_response.path = folder.get_path()
        folder_response.depth = folder.get_depth()

        return StandardResponse(
            data=folder_response,
            message="Folder moved successfully",
        )
    except ValueError as e:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
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

    file_service = FileService(service.db)

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
        folder_response.path = folder.get_path()
        folder_response.depth = folder.get_depth()
        path_responses.append(folder_response)

    return StandardListResponse(
        data=path_responses,
        message="Folder path retrieved successfully",
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
        folder_response.path = folder.get_path()
        folder_response.depth = folder.get_depth()
        folder_responses.append(folder_response)

    return StandardListResponse(
        data=folder_responses,
        message="Folders retrieved successfully",
    )

