"""Search repository for data access operations."""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.search_index import SearchIndex


class SearchRepository:
    """Repository for search index data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_index(self, index_data: dict) -> SearchIndex:
        """Create a new search index entry."""
        index = SearchIndex(**index_data)
        self.db.add(index)
        self.db.commit()
        self.db.refresh(index)
        return index

    def get_index_by_entity(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID
    ) -> SearchIndex | None:
        """Get search index by entity."""
        return (
            self.db.query(SearchIndex)
            .filter(
                SearchIndex.entity_type == entity_type,
                SearchIndex.entity_id == entity_id,
                SearchIndex.tenant_id == tenant_id,
            )
            .first()
        )

    def update_index(
        self, entity_type: str, entity_id: UUID, tenant_id: UUID, index_data: dict
    ) -> SearchIndex | None:
        """Update a search index entry."""
        index = self.get_index_by_entity(entity_type, entity_id, tenant_id)
        if not index:
            return None
        for key, value in index_data.items():
            setattr(index, key, value)
        self.db.commit()
        self.db.refresh(index)
        return index

    def delete_index(self, entity_type: str, entity_id: UUID, tenant_id: UUID) -> bool:
        """Delete a search index entry."""
        index = self.get_index_by_entity(entity_type, entity_id, tenant_id)
        if not index:
            return False
        self.db.delete(index)
        self.db.commit()
        return True

    def search(
        self,
        tenant_id: UUID,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 50,
    ) -> list[SearchIndex]:
        """Search across all indexed entities."""
        search_query = self.db.query(SearchIndex).filter(SearchIndex.tenant_id == tenant_id)

        # Filter by entity types if provided
        if entity_types:
            search_query = search_query.filter(SearchIndex.entity_type.in_(entity_types))

        # Full-text search using PostgreSQL ts_vector
        # Using ilike for simple search (can be enhanced with full-text search)
        search_query = search_query.filter(
            or_(
                SearchIndex.title.ilike(f"%{query}%"),
                SearchIndex.content.ilike(f"%{query}%"),
            )
        )

        return search_query.limit(limit).all()

    def get_all_by_entity_type(
        self, tenant_id: UUID, entity_type: str, skip: int = 0, limit: int = 100
    ) -> list[SearchIndex]:
        """Get all indices for a specific entity type."""
        return (
            self.db.query(SearchIndex)
            .filter(SearchIndex.tenant_id == tenant_id, SearchIndex.entity_type == entity_type)
            .offset(skip)
            .limit(limit)
            .all()
        )








