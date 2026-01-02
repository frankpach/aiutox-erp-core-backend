"""Repository for folder data access."""

from typing import List
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.folder import Folder, FolderPermission


class FolderRepository:
    """Repository for folder operations."""

    def __init__(self, db: Session):
        """Initialize folder repository.

        Args:
            db: Database session
        """
        self.db = db

    def create(self, folder_data: dict) -> Folder:
        """Create a new folder.

        Args:
            folder_data: Folder data dictionary

        Returns:
            Created Folder object
        """
        folder = Folder(**folder_data)
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def get_by_id(self, folder_id: UUID, tenant_id: UUID) -> Folder | None:
        """Get folder by ID with tenant check.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID

        Returns:
            Folder object or None
        """
        return (
            self.db.query(Folder)
            .filter(and_(Folder.id == folder_id, Folder.tenant_id == tenant_id))
            .first()
        )

    def get_by_parent(
        self, parent_id: UUID | None, tenant_id: UUID, entity_type: str | None = None, entity_id: UUID | None = None
    ) -> List[Folder]:
        """Get folders by parent ID.

        Args:
            parent_id: Parent folder ID (None for root folders)
            tenant_id: Tenant ID
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter

        Returns:
            List of Folder objects
        """
        query = self.db.query(Folder).filter(
            and_(
                Folder.tenant_id == tenant_id,
                Folder.parent_id == parent_id,
            )
        )

        if entity_type:
            query = query.filter(Folder.entity_type == entity_type)
        if entity_id:
            query = query.filter(Folder.entity_id == entity_id)

        return query.order_by(Folder.name).all()

    def get_tree(self, tenant_id: UUID, parent_id: UUID | None = None, entity_type: str | None = None, entity_id: UUID | None = None) -> List[Folder]:
        """Get folder tree starting from a parent.

        Args:
            tenant_id: Tenant ID
            parent_id: Parent folder ID (None for root)
            entity_type: Optional entity type filter
            entity_id: Optional entity ID filter

        Returns:
            List of Folder objects with children loaded
        """
        query = self.db.query(Folder).filter(
            and_(
                Folder.tenant_id == tenant_id,
                Folder.parent_id == parent_id,
            )
        )

        if entity_type:
            query = query.filter(Folder.entity_type == entity_type)
        if entity_id:
            query = query.filter(Folder.entity_id == entity_id)

        # Use selectinload for recursive loading of children
        return query.options(selectinload(Folder.children)).order_by(Folder.name).all()

    def update(self, folder_id: UUID, tenant_id: UUID, folder_data: dict) -> Folder | None:
        """Update a folder.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID
            folder_data: Folder data to update

        Returns:
            Updated Folder object or None
        """
        folder = self.get_by_id(folder_id, tenant_id)
        if not folder:
            return None

        for key, value in folder_data.items():
            if value is not None:
                setattr(folder, key, value)

        self.db.commit()
        self.db.refresh(folder)
        return folder

    def delete(self, folder_id: UUID, tenant_id: UUID) -> bool:
        """Delete a folder.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        folder = self.get_by_id(folder_id, tenant_id)
        if not folder:
            return False

        # Check if folder has children or files
        children_count = self.db.query(Folder).filter(Folder.parent_id == folder_id).count()
        files_count = folder.files.count()

        if children_count > 0 or files_count > 0:
            raise ValueError("Cannot delete folder with children or files. Move or delete them first.")

        self.db.delete(folder)
        self.db.commit()
        return True

    def move(self, folder_id: UUID, tenant_id: UUID, new_parent_id: UUID | None) -> Folder | None:
        """Move a folder to a new parent.

        Args:
            folder_id: Folder ID to move
            tenant_id: Tenant ID
            new_parent_id: New parent folder ID (None for root)

        Returns:
            Updated Folder object or None
        """
        folder = self.get_by_id(folder_id, tenant_id)
        if not folder:
            return None

        # Prevent moving folder into itself or its descendants
        if new_parent_id:
            new_parent = self.get_by_id(new_parent_id, tenant_id)
            if not new_parent:
                raise ValueError("Target parent folder not found")

            # Check if new_parent is a descendant of folder
            current = new_parent.parent
            while current:
                if current.id == folder_id:
                    raise ValueError("Cannot move folder into its own descendant")
                current = current.parent

        folder.parent_id = new_parent_id
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def search(self, tenant_id: UUID, query: str, entity_type: str | None = None) -> List[Folder]:
        """Search folders by name.

        Args:
            tenant_id: Tenant ID
            query: Search query
            entity_type: Optional entity type filter

        Returns:
            List of matching Folder objects
        """
        search_query = self.db.query(Folder).filter(
            and_(
                Folder.tenant_id == tenant_id,
                Folder.name.ilike(f"%{query}%"),
            )
        )

        if entity_type:
            search_query = search_query.filter(Folder.entity_type == entity_type)

        return search_query.order_by(Folder.name).limit(100).all()

    def get_path(self, folder_id: UUID, tenant_id: UUID) -> List[Folder]:
        """Get the path from root to folder (breadcrumbs).

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID

        Returns:
            List of Folder objects from root to folder
        """
        folder = self.get_by_id(folder_id, tenant_id)
        if not folder:
            return []

        path = []
        current = folder
        while current:
            path.insert(0, current)
            if current.parent_id:
                current = self.get_by_id(current.parent_id, tenant_id)
            else:
                current = None

        return path

    def create_permission(self, permission_data: dict) -> FolderPermission:
        """Create a new folder permission.

        Args:
            permission_data: Permission data dictionary

        Returns:
            Created FolderPermission object
        """
        permission = FolderPermission(**permission_data)
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def get_permissions(self, folder_id: UUID, tenant_id: UUID) -> list[FolderPermission]:
        """Get all permissions for a folder.

        Args:
            folder_id: Folder ID
            tenant_id: Tenant ID

        Returns:
            List of FolderPermission objects
        """
        return (
            self.db.query(FolderPermission)
            .filter(
                FolderPermission.folder_id == folder_id,
                FolderPermission.tenant_id == tenant_id,
            )
            .all()
        )

    def update_permission(
        self, permission_id: UUID, tenant_id: UUID, permission_data: dict
    ) -> FolderPermission | None:
        """Update a folder permission.

        Args:
            permission_id: Permission ID
            tenant_id: Tenant ID
            permission_data: Permission data to update

        Returns:
            Updated FolderPermission object or None
        """
        permission = (
            self.db.query(FolderPermission)
            .filter(
                FolderPermission.id == permission_id,
                FolderPermission.tenant_id == tenant_id,
            )
            .first()
        )
        if not permission:
            return None

        for key, value in permission_data.items():
            if value is not None:
                setattr(permission, key, value)

        self.db.commit()
        self.db.refresh(permission)
        return permission

    def delete_permission(self, permission_id: UUID, tenant_id: UUID) -> bool:
        """Delete a folder permission.

        Args:
            permission_id: Permission ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        permission = (
            self.db.query(FolderPermission)
            .filter(
                FolderPermission.id == permission_id,
                FolderPermission.tenant_id == tenant_id,
            )
            .first()
        )
        if not permission:
            return False

        self.db.delete(permission)
        self.db.commit()
        return True


