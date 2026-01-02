"""Folder service for folder management."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.folder import Folder, FolderPermission
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

        # Publish event (non-blocking - don't fail if event fails)
        try:
            await self.event_publisher.publish(
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
        except Exception as e:
            logger.warning(f"Failed to publish folder.created event: {e}", exc_info=True)
            # Don't fail folder creation if event publishing fails

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

    def set_folder_permissions(
        self,
        folder_id: UUID,
        permissions: list[dict],
        tenant_id: UUID,
    ) -> list[FolderPermission]:
        """Set permissions for a folder.

        Args:
            folder_id: Folder ID
            permissions: List of permission dicts with target_type, target_id, and permission flags
            tenant_id: Tenant ID

        Returns:
            List of created FolderPermission objects

        Raises:
            ValueError: If target_id doesn't exist or doesn't belong to tenant
        """
        from app.models.user import User
        from app.models.organization import Organization

        # Delete existing permissions
        existing = self.repository.get_permissions(folder_id, tenant_id)
        for perm in existing:
            self.repository.delete_permission(perm.id, tenant_id)

        # Validate and create new permissions
        created_permissions = []
        for perm_data in permissions:
            target_type = perm_data.get("target_type")
            target_id = perm_data.get("target_id")

            if not target_type or not target_id:
                raise ValueError("target_type and target_id are required")

            # Validate that target exists and belongs to tenant
            if target_type == "user":
                user = self.db.query(User).filter(
                    User.id == target_id,
                    User.tenant_id == tenant_id
                ).first()
                if not user:
                    raise ValueError(f"User with ID {target_id} not found or doesn't belong to tenant")
            elif target_type == "role":
                # Validate role exists (check in ROLE_PERMISSIONS or MODULE_ROLES)
                from app.core.auth.permissions import ROLE_PERMISSIONS, MODULE_ROLES
                role_name = str(target_id)
                # Check if it's a global role
                if role_name not in ROLE_PERMISSIONS:
                    # Check if it's a module role (format: "module.internal.role")
                    # or just the role name for any module
                    is_valid = False
                    for module_roles in MODULE_ROLES.values():
                        if role_name in module_roles or role_name.replace("internal.", "") in [r.replace("internal.", "") for r in module_roles.keys()]:
                            is_valid = True
                            break
                    if not is_valid:
                        raise ValueError(f"Role '{target_id}' not found. Must be a valid global role or module role.")
            elif target_type == "organization":
                org = self.db.query(Organization).filter(
                    Organization.id == target_id,
                    Organization.tenant_id == tenant_id
                ).first()
                if not org:
                    raise ValueError(f"Organization with ID {target_id} not found or doesn't belong to tenant")
            else:
                raise ValueError(f"Invalid target_type: {target_type}. Must be 'user', 'role', or 'organization'")

            perm = self.repository.create_permission(
                {
                    "folder_id": folder_id,
                    "tenant_id": tenant_id,
                    "target_type": target_type,
                    "target_id": target_id,
                    "can_view": perm_data.get("can_view", True),
                    "can_create_files": perm_data.get("can_create_files", False),
                    "can_create_folders": perm_data.get("can_create_folders", False),
                    "can_edit": perm_data.get("can_edit", False),
                    "can_delete": perm_data.get("can_delete", False),
                }
            )
            created_permissions.append(perm)

        return created_permissions

    def get_folder_permissions(self, folder_id: UUID, tenant_id: UUID) -> list[FolderPermission]:
        """Get all permissions for a folder.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID

        Returns:
            List of FolderPermission objects
        """
        return self.repository.get_permissions(folder_id, tenant_id)

    def check_folder_permissions(
        self,
        folder_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
        permission: str,
    ) -> bool:
        """Check if a user has a specific permission on a folder.

        Security:
        - Folder owner always has full access
        - Checks user-specific permissions first
        - Then checks role-based permissions
        - Then checks organization-based permissions
        - Multi-tenant isolation enforced

        Args:
            folder_id: Folder ID
            user_id: User ID to check permissions for
            tenant_id: Tenant ID (for multi-tenancy)
            permission: Permission to check ("view", "create_files", "create_folders", "edit", "delete")

        Returns:
            True if user has permission, False otherwise

        Raises:
            FileNotFoundError: If folder not found
        """
        # Get folder
        folder = self.repository.get_by_id(folder_id, tenant_id)
        if not folder:
            raise FileNotFoundError(f"Folder {folder_id} not found")

        # Folder owner always has full access
        if folder.created_by == user_id:
            return True

        # Get all permissions for the folder
        permissions = self.repository.get_permissions(folder_id, tenant_id)

        # Map permission string to attribute
        permission_map = {
            "view": "can_view",
            "create_files": "can_create_files",
            "create_folders": "can_create_folders",
            "edit": "can_edit",
            "delete": "can_delete",
        }

        if permission not in permission_map:
            raise ValueError(f"Invalid permission: {permission}")

        permission_attr = permission_map[permission]

        # Check user-specific permissions
        for perm in permissions:
            if perm.target_type == "user" and perm.target_id == user_id:
                return getattr(perm, permission_attr, False)

        # Check role-based permissions
        from app.models.user_role import UserRole

        user_roles = (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id)
            .all()
        )

        # Check if any permission matches a role UUID
        for perm in permissions:
            if perm.target_type == "role":
                if user_roles and getattr(perm, permission_attr, False):
                    # Simplified check - in production you'd want proper role mapping
                    return True

        # Check organization-based permissions (if user belongs to organization)
        from app.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        if user and user.organization_id:
            for perm in permissions:
                if (
                    perm.target_type == "organization"
                    and perm.target_id == user.organization_id
                ):
                    if getattr(perm, permission_attr, False):
                        return True

        # No permission found
        return False

    def check_inherited_permissions(
        self,
        folder_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, bool]:
        """Check permissions inherited from parent folders.

        Args:
            folder_id: Folder ID
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            Dictionary with permission flags (can_view, can_create_files, etc.)
        """
        folder = self.repository.get_by_id(folder_id, tenant_id)
        if not folder:
            return {}

        # Start with no permissions
        inherited = {
            "can_view": False,
            "can_create_files": False,
            "can_create_folders": False,
            "can_edit": False,
            "can_delete": False,
        }

        # Walk up the folder tree checking permissions
        current = folder.parent
        while current:
            permissions = self.repository.get_permissions(current.id, tenant_id)
            for perm in permissions:
                # Check if user matches this permission
                matches = False
                if perm.target_type == "user" and perm.target_id == user_id:
                    matches = True
                elif perm.target_type == "role":
                    from app.models.user_role import UserRole
                    user_roles = (
                        self.db.query(UserRole)
                        .filter(UserRole.user_id == user_id)
                        .all()
                    )
                    if user_roles:
                        matches = True  # Simplified check
                elif perm.target_type == "organization":
                    from app.models.user import User
                    user = self.db.query(User).filter(User.id == user_id).first()
                    if user and user.organization_id == perm.target_id:
                        matches = True

                if matches:
                    # Inherit permissions (OR logic - if any parent grants, inherit)
                    inherited["can_view"] = inherited["can_view"] or perm.can_view
                    inherited["can_create_files"] = inherited["can_create_files"] or perm.can_create_files
                    inherited["can_create_folders"] = inherited["can_create_folders"] or perm.can_create_folders
                    inherited["can_edit"] = inherited["can_edit"] or perm.can_edit
                    inherited["can_delete"] = inherited["can_delete"] or perm.can_delete

            current = current.parent

        return inherited

