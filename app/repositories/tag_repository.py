"""Tag repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tag import EntityTag, Tag, TagCategory


class TagRepository:
    """Repository for tag data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Tag operations
    def create_tag(self, tag_data: dict) -> Tag:
        """Create a new tag."""
        tag = Tag(**tag_data)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def get_tag_by_id(self, tag_id: UUID, tenant_id: UUID) -> Tag | None:
        """Get tag by ID and tenant."""
        return (
            self.db.query(Tag)
            .filter(Tag.id == tag_id, Tag.tenant_id == tenant_id, Tag.is_active)
            .first()
        )

    def get_all_tags(
        self, tenant_id: UUID, category_id: UUID | None = None, active_only: bool = True
    ) -> list[Tag]:
        """Get all tags for a tenant."""
        query = self.db.query(Tag).filter(Tag.tenant_id == tenant_id)
        if active_only:
            query = query.filter(Tag.is_active)
        if category_id:
            query = query.filter(Tag.category_id == category_id)
        return query.order_by(Tag.name).all()

    def search_tags(self, tenant_id: UUID, query_text: str) -> list[Tag]:
        """Search tags by name."""
        return (
            self.db.query(Tag)
            .filter(
                Tag.tenant_id == tenant_id,
                Tag.is_active,
                Tag.name.ilike(f"%{query_text}%"),
            )
            .order_by(Tag.name)
            .all()
        )

    def update_tag(self, tag_id: UUID, tenant_id: UUID, tag_data: dict) -> Tag | None:
        """Update a tag."""
        tag = self.get_tag_by_id(tag_id, tenant_id)
        if not tag:
            return None
        for key, value in tag_data.items():
            setattr(tag, key, value)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete_tag(self, tag_id: UUID, tenant_id: UUID) -> bool:
        """Delete a tag (soft delete)."""
        tag = self.get_tag_by_id(tag_id, tenant_id)
        if not tag:
            return False
        tag.is_active = False
        self.db.commit()
        return True

    # TagCategory operations
    def create_category(self, category_data: dict) -> TagCategory:
        """Create a new tag category."""
        category = TagCategory(**category_data)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def get_category_by_id(
        self, category_id: UUID, tenant_id: UUID
    ) -> TagCategory | None:
        """Get category by ID and tenant."""
        return (
            self.db.query(TagCategory)
            .filter(TagCategory.id == category_id, TagCategory.tenant_id == tenant_id)
            .first()
        )

    def get_all_categories(self, tenant_id: UUID) -> list[TagCategory]:
        """Get all categories for a tenant."""
        return (
            self.db.query(TagCategory)
            .filter(TagCategory.tenant_id == tenant_id)
            .order_by(TagCategory.sort_order, TagCategory.name)
            .all()
        )

    # EntityTag operations
    def create_entity_tag(self, entity_tag_data: dict) -> EntityTag:
        """Create a new entity-tag relationship."""
        entity_tag = EntityTag(**entity_tag_data)
        self.db.add(entity_tag)
        self.db.commit()
        self.db.refresh(entity_tag)
        return entity_tag

    def get_entity_tags(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> list[Tag]:
        """Get all tags for an entity."""
        entity_tags = (
            self.db.query(EntityTag)
            .filter(
                EntityTag.entity_type == entity_type,
                EntityTag.entity_id == entity_id,
                EntityTag.tenant_id == tenant_id,
            )
            .all()
        )

        tag_ids = [et.tag_id for et in entity_tags]
        if not tag_ids:
            return []

        return self.db.query(Tag).filter(Tag.id.in_(tag_ids), Tag.is_active).all()

    def remove_entity_tag(
        self, tag_id: UUID, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> bool:
        """Remove a tag from an entity."""
        entity_tag = (
            self.db.query(EntityTag)
            .filter(
                EntityTag.tag_id == tag_id,
                EntityTag.entity_type == entity_type,
                EntityTag.entity_id == entity_id,
                EntityTag.tenant_id == tenant_id,
            )
            .first()
        )
        if not entity_tag:
            return False
        self.db.delete(entity_tag)
        self.db.commit()
        return True

    def entity_has_tag(
        self, tag_id: UUID, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> bool:
        """Check if entity has a specific tag."""
        return (
            self.db.query(EntityTag)
            .filter(
                EntityTag.tag_id == tag_id,
                EntityTag.entity_type == entity_type,
                EntityTag.entity_id == entity_id,
                EntityTag.tenant_id == tenant_id,
            )
            .first()
            is not None
        )
