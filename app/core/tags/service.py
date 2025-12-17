"""Tag service for tag management."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tag import EntityTag, Tag, TagCategory
from app.repositories.tag_repository import TagRepository

logger = logging.getLogger(__name__)


class TagService:
    """Service for tag management."""

    def __init__(self, db: Session):
        """Initialize tag service.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = TagRepository(db)

    def create_tag(
        self,
        name: str,
        tenant_id: UUID,
        color: str | None = None,
        description: str | None = None,
        category_id: UUID | None = None,
    ) -> Tag:
        """Create a new tag.

        Args:
            name: Tag name
            tenant_id: Tenant ID
            color: Hex color code (optional)
            description: Tag description (optional)
            category_id: Category ID (optional)

        Returns:
            Created Tag object
        """
        tag = self.repository.create_tag(
            {
                "tenant_id": tenant_id,
                "name": name,
                "color": color,
                "description": description,
                "category_id": category_id,
            }
        )

        logger.info(f"Tag created: {tag.id} ({name})")
        return tag

    def add_tag_to_entity(
        self,
        tag_id: UUID,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
    ) -> EntityTag:
        """Add a tag to an entity.

        Args:
            tag_id: Tag ID
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID

        Returns:
            Created EntityTag object
        """
        # Check if tag exists and is active
        tag = self.repository.get_tag_by_id(tag_id, tenant_id)
        if not tag:
            raise ValueError(f"Tag {tag_id} not found or inactive")

        # Check if already tagged
        if self.repository.entity_has_tag(tag_id, entity_type, entity_id, tenant_id):
            raise ValueError(f"Entity {entity_type}:{entity_id} already has tag {tag_id}")

        entity_tag = self.repository.create_entity_tag(
            {
                "tenant_id": tenant_id,
                "tag_id": tag_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
            }
        )

        logger.info(f"Tag {tag_id} added to {entity_type}:{entity_id}")
        return entity_tag

    def remove_tag_from_entity(
        self,
        tag_id: UUID,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
    ) -> bool:
        """Remove a tag from an entity.

        Args:
            tag_id: Tag ID
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID

        Returns:
            True if removed successfully
        """
        removed = self.repository.remove_entity_tag(
            tag_id, entity_type, entity_id, tenant_id
        )

        if removed:
            logger.info(f"Tag {tag_id} removed from {entity_type}:{entity_id}")

        return removed

    def get_entity_tags(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> list[Tag]:
        """Get all tags for an entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID

        Returns:
            List of Tag objects
        """
        return self.repository.get_entity_tags(entity_type, entity_id, tenant_id)

    def get_tags_by_category(
        self, category_id: UUID, tenant_id: UUID
    ) -> list[Tag]:
        """Get all tags in a category.

        Args:
            category_id: Category ID
            tenant_id: Tenant ID

        Returns:
            List of Tag objects
        """
        return self.repository.get_all_tags(tenant_id, category_id=category_id)

    def search_tags(self, tenant_id: UUID, query: str) -> list[Tag]:
        """Search tags by name.

        Args:
            tenant_id: Tenant ID
            query: Search query

        Returns:
            List of Tag objects matching the search
        """
        return self.repository.search_tags(tenant_id, query)

    def get_tag(self, tag_id: UUID, tenant_id: UUID) -> Tag | None:
        """Get a tag by ID.

        Args:
            tag_id: Tag ID
            tenant_id: Tenant ID

        Returns:
            Tag object or None if not found
        """
        return self.repository.get_tag_by_id(tag_id, tenant_id)

    def get_all_tags(
        self, tenant_id: UUID, category_id: UUID | None = None
    ) -> list[Tag]:
        """Get all tags for a tenant.

        Args:
            tenant_id: Tenant ID
            category_id: Filter by category (optional)

        Returns:
            List of Tag objects
        """
        return self.repository.get_all_tags(tenant_id, category_id=category_id)

    def update_tag(
        self,
        tag_id: UUID,
        tenant_id: UUID,
        name: str | None = None,
        color: str | None = None,
        description: str | None = None,
        category_id: UUID | None = None,
    ) -> Tag | None:
        """Update a tag.

        Args:
            tag_id: Tag ID
            tenant_id: Tenant ID
            name: New name (optional)
            color: New color (optional)
            description: New description (optional)
            category_id: New category ID (optional)

        Returns:
            Updated Tag object or None if not found
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if color is not None:
            update_data["color"] = color
        if description is not None:
            update_data["description"] = description
        if category_id is not None:
            update_data["category_id"] = category_id

        return self.repository.update_tag(tag_id, tenant_id, update_data)

    def delete_tag(self, tag_id: UUID, tenant_id: UUID) -> bool:
        """Delete a tag (soft delete).

        Args:
            tag_id: Tag ID
            tenant_id: Tenant ID

        Returns:
            True if deleted successfully
        """
        return self.repository.delete_tag(tag_id, tenant_id)

    # TagCategory methods
    def create_category(
        self,
        name: str,
        tenant_id: UUID,
        color: str | None = None,
        description: str | None = None,
        parent_id: UUID | None = None,
        sort_order: int = 0,
    ) -> TagCategory:
        """Create a new tag category."""
        category = self.repository.create_category(
            {
                "tenant_id": tenant_id,
                "name": name,
                "color": color,
                "description": description,
                "parent_id": parent_id,
                "sort_order": sort_order,
            }
        )
        return category

    def get_all_categories(self, tenant_id: UUID) -> list[TagCategory]:
        """Get all categories for a tenant."""
        return self.repository.get_all_categories(tenant_id)

