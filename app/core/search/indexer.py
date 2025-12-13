"""Search indexer for indexing entities."""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.search_index import SearchIndex
from app.repositories.search_repository import SearchRepository

logger = logging.getLogger(__name__)


class SearchIndexer:
    """Indexer for creating and updating search indices."""

    def __init__(self, db: Session):
        """Initialize search indexer.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = SearchRepository(db)

    def index_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        title: str,
        content: str | None = None,
        metadata: dict | None = None,
    ) -> SearchIndex:
        """Index an entity for search.

        Args:
            entity_type: Entity type (e.g., 'product', 'contact')
            entity_id: Entity ID
            tenant_id: Tenant ID
            title: Entity title
            content: Entity content for search (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created or updated SearchIndex object
        """
        # Check if index already exists
        existing = self.repository.get_index_by_entity(entity_type, entity_id, tenant_id)

        import json

        index_data = {
            "tenant_id": tenant_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "title": title,
            "content": content,
            "metadata": json.dumps(metadata) if metadata else None,
        }

        if existing:
            # Update existing index
            index = self.repository.update_index(entity_type, entity_id, tenant_id, index_data)
        else:
            # Create new index
            index = self.repository.create_index(index_data)

        logger.info(f"Entity indexed: {entity_type}:{entity_id}")
        return index

    def remove_index(self, entity_type: str, entity_id: UUID, tenant_id: UUID) -> bool:
        """Remove an entity from search index.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID

        Returns:
            True if removed successfully, False otherwise
        """
        deleted = self.repository.delete_index(entity_type, entity_id, tenant_id)
        if deleted:
            logger.info(f"Entity removed from index: {entity_type}:{entity_id}")
        return deleted

    def reindex_entity_type(self, tenant_id: UUID, entity_type: str) -> int:
        """Reindex all entities of a specific type.

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type to reindex

        Returns:
            Number of entities reindexed
        """
        # This would typically call a service method to get all entities
        # and reindex them. For now, we'll just return 0 as a placeholder.
        # In a real implementation, this would:
        # 1. Get all entities of the type
        # 2. For each entity, call index_entity with its data
        logger.info(f"Reindexing {entity_type} for tenant {tenant_id}")
        return 0

