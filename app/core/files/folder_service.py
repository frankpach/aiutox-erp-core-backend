"""Folder service for folder management."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.folder import Folder
from app.repositories.folder_repository import FolderRepository

logger = logging.getLogger(__name__)


class FolderService:
    """Service for folder management."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize folder service.

        Args:
            db: Database session
            event_publisher: EventPublisher instance (created if not provided)
        """
        self.db = db
        self.repository = FolderRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()

    async def create_folder(
        self,
        name: str,
        tenant_id: UUID,
        user_id: UUID,
        parent_id: UUID | None = None,
        description: str | None = None,
        color: str | None = None,
        icon: str | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> Folder:
        """Create a new folder.

        Args:
            name: Folder name
            tenant_id: Tenant ID
            user_id: User ID who created the folder
            parent_id: Parent folder ID (None for root)
            description: Folder description
            color: Folder color (hex)
            icon: Folder icon name
            entity_type: Entity type
            entity_id: Entity ID
            metadata: Additional metadata

        Returns:
            Created Folder object
        """
        # Check if folder name already exists in parent
        existing = self.repository.get_by_parent(parent_id, tenant_id)
        if any(f.name.lower() == name.lower() for f in existing):
            raise ValueError(f"Folder with name '{name}' already exists in this location")

        folder = self.repository.create(
            {
                "name": name,
                "description": description,
                "color": color,
                "icon": icon,
                "parent_id": parent_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "metadata": metadata,
                "tenant_id": tenant_id,
                "created_by": user_id,
            }
        )

        # Publish event
        self.event_publisher.publish(
            event_type="folder.created",
            entity_type="folder",
            entity_id=folder.id,
            tenant_id=tenant_id,
            user_id=user_id,
            metadata=EventMetadata(
                source="folder_service",
                version="1.0",
                additional_data={
                    "name": name,
                    "parent_id": str(parent_id) if parent_id else None,
                },
            ),
        )

        logger.info(f"Folder created: {folder.id} ({name})")
        return folder

    async def get_folder(self, folder_id: UUID, tenant_id: UUID) -> Folder | None:
        """Get a folder by ID.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID

        Returns:
            Folder object or None
        """
        return self.repository.get_by_id(folder_id, tenant_id)

    async def list_folders(
        self,
        tenant_id: UUID,
        parent_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> list[Folder]:
        """List folders.

        Args:
            tenant_id: Tenant ID
            parent_id: Parent folder ID (None for root)
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter

        Returns:
            List of Folder objects
        """
        return self.repository.get_by_parent(parent_id, tenant_id, entity_type, entity_id)

    async def get_folder_tree(
        self,
        tenant_id: UUID,
        parent_id: UUID | None = None,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> list[Folder]:
        """Get folder tree.

        Args:
            tenant_id: Tenant ID
            parent_id: Parent folder ID (None for root)
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter

        Returns:
            List of Folder objects with children
        """
        return self.repository.get_tree(tenant_id, parent_id, entity_type, entity_id)

    async def update_folder(
        self,
        folder_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        name: str | None = None,
        description: str | None = None,
        color: str | None = None,
        icon: str | None = None,
        metadata: dict | None = None,
    ) -> Folder | None:
        """Update a folder.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID
            user_id: User ID
            name: New folder name
            description: New description
            color: New color
            icon: New icon
            metadata: New metadata

        Returns:
            Updated Folder object or None
        """
        folder = self.repository.get_by_id(folder_id, tenant_id)
        if not folder:
            return None

        # Check name uniqueness if name is being changed
        if name and name != folder.name:
            existing = self.repository.get_by_parent(folder.parent_id, tenant_id)
            if any(f.name.lower() == name.lower() and f.id != folder_id for f in existing):
                raise ValueError(f"Folder with name '{name}' already exists in this location")

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if color is not None:
            update_data["color"] = color
        if icon is not None:
            update_data["icon"] = icon
        if metadata is not None:
            update_data["metadata"] = metadata

        updated_folder = self.repository.update(folder_id, tenant_id, update_data)

        if updated_folder:
            # Publish event
            await self.event_publisher.publish(
                event_type="folder.updated",
                entity_type="folder",
                entity_id=folder_id,
                tenant_id=tenant_id,
                user_id=user_id,
                metadata=EventMetadata(
                    source="folder_service",
                    version="1.0",
                    additional_data={"changes": list(update_data.keys())},
                ),
            )

        return updated_folder

    async def delete_folder(self, folder_id: UUID, tenant_id: UUID, user_id: UUID) -> bool:
        """Delete a folder.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        folder = self.repository.get_by_id(folder_id, tenant_id)
        if not folder:
            return False

        try:
            deleted = self.repository.delete(folder_id, tenant_id)
            if deleted:
                # Publish event
                await self.event_publisher.publish(
                    event_type="folder.deleted",
                    entity_type="folder",
                    entity_id=folder_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    metadata=EventMetadata(
                        source="folder_service",
                        version="1.0",
                        additional_data={"name": folder.name},
                    ),
                )
            return deleted
        except ValueError as e:
            logger.error(f"Error deleting folder {folder_id}: {e}")
            raise

    async def move_folder(self, folder_id: UUID, tenant_id: UUID, user_id: UUID, new_parent_id: UUID | None) -> Folder | None:
        """Move a folder to a new parent.

        Args:
            folder_id: Folder ID to move
            tenant_id: Tenant ID
            user_id: User ID
            new_parent_id: New parent folder ID (None for root)

        Returns:
            Updated Folder object or None
        """
        folder = self.repository.get_by_id(folder_id, tenant_id)
        if not folder:
            return None

        # Check name uniqueness in new location
        existing = self.repository.get_by_parent(new_parent_id, tenant_id)
        if any(f.name.lower() == folder.name.lower() and f.id != folder_id for f in existing):
            raise ValueError(f"Folder with name '{folder.name}' already exists in target location")

        moved_folder = self.repository.move(folder_id, tenant_id, new_parent_id)

        if moved_folder:
            # Publish event
            await self.event_publisher.publish(
                event_type="folder.moved",
                entity_type="folder",
                entity_id=folder_id,
                tenant_id=tenant_id,
                user_id=user_id,
                metadata=EventMetadata(
                    source="folder_service",
                    version="1.0",
                    additional_data={
                        "old_parent_id": str(folder.parent_id) if folder.parent_id else None,
                        "new_parent_id": str(new_parent_id) if new_parent_id else None,
                    },
                ),
            )

        return moved_folder

    async def get_folder_path(self, folder_id: UUID, tenant_id: UUID) -> list[Folder]:
        """Get the path (breadcrumbs) from root to folder.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID

        Returns:
            List of Folder objects from root to folder
        """
        return self.repository.get_path(folder_id, tenant_id)

    async def search_folders(self, tenant_id: UUID, query: str, entity_type: str | None = None) -> list[Folder]:
        """Search folders by name.

        Args:
            tenant_id: Tenant ID
            query: Search query
            entity_type: Optional entity type filter

        Returns:
            List of matching Folder objects
        """
        return self.repository.search(tenant_id, query, entity_type)

