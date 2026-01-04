"""Search service for high-level search operations."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.search.engine import SearchEngine
from app.core.search.indexer import SearchIndexer
from app.core.pubsub import EventPublisher
from app.repositories.search_repository import SearchRepository

logger = logging.getLogger(__name__)


class SearchService:
    """High-level service for search operations."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize search service.

        Args:
            db: Database session
            event_publisher: Event publisher for search events
        """
        self.db = db
        self.repository = SearchRepository(db)
        self.engine = SearchEngine(db)
        self.indexer = SearchIndexer(db)
        self.event_publisher = event_publisher

    def search(
        self,
        tenant_id: UUID,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search across all indexed entities.

        Args:
            tenant_id: Tenant ID
            query: Search query
            entity_types: Filter by entity types (optional)
            limit: Maximum number of results (default: 50)

        Returns:
            Dictionary with search results categorized by entity type
        """
        results = self.engine.search(tenant_id, query, entity_types, limit)

        # Log search event
        if self.event_publisher:
            self.event_publisher.publish(
                event_type="search.performed",
                entity_type="search",
                entity_id=None,
                tenant_id=tenant_id,
                data={
                    "query": query,
                    "entity_types": entity_types,
                    "results_count": results["total"],
                },
            )

        return results

    def get_suggestions(
        self, tenant_id: UUID, query: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get search suggestions.

        Args:
            tenant_id: Tenant ID
            query: Search query
            limit: Maximum number of suggestions (default: 10)

        Returns:
            List of suggestion dictionaries
        """
        return self.engine.get_suggestions(tenant_id, query, limit)

    def index_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        title: str,
        content: str | None = None,
        metadata: dict | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Index an entity for search.

        Args:
            entity_type: Entity type (e.g., 'product', 'contact')
            entity_id: Entity ID
            tenant_id: Tenant ID
            title: Entity title
            content: Entity content for search (optional)
            metadata: Additional metadata (optional)
            user_id: User ID performing the action (optional)

        Returns:
            Dictionary with indexed entity information
        """
        index = self.indexer.index_entity(
            entity_type, entity_id, tenant_id, title, content, metadata
        )

        # Log indexing event
        if self.event_publisher:
            self.event_publisher.publish(
                event_type="search.entity_indexed",
                entity_type=entity_type,
                entity_id=entity_id,
                tenant_id=tenant_id,
                user_id=user_id,
                data={
                    "title": title,
                    "has_content": content is not None,
                    "has_metadata": metadata is not None,
                },
            )

        return {
            "id": str(index.id),
            "entity_type": index.entity_type,
            "entity_id": str(index.entity_id),
            "title": index.title,
            "indexed_at": index.created_at.isoformat(),
        }

    def remove_index(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        user_id: UUID | None = None,
    ) -> bool:
        """Remove an entity from search index.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            tenant_id: Tenant ID
            user_id: User ID performing the action (optional)

        Returns:
            True if removed successfully, False otherwise
        """
        deleted = self.indexer.remove_index(entity_type, entity_id, tenant_id)

        # Log removal event
        if self.event_publisher and deleted:
            self.event_publisher.publish(
                event_type="search.entity_removed",
                entity_type=entity_type,
                entity_id=entity_id,
                tenant_id=tenant_id,
                user_id=user_id,
                data={},
            )

        return deleted

    def reindex_entity_type(
        self, tenant_id: UUID, entity_type: str, user_id: UUID | None = None
    ) -> dict[str, Any]:
        """Reindex all entities of a specific type.

        Args:
            tenant_id: Tenant ID
            entity_type: Entity type to reindex
            user_id: User ID performing the action (optional)

        Returns:
            Dictionary with reindexing results
        """
        count = self.indexer.reindex_entity_type(tenant_id, entity_type)

        # Log reindexing event
        if self.event_publisher:
            self.event_publisher.publish(
                event_type="search.entity_type_reindexed",
                entity_type=entity_type,
                entity_id=None,
                tenant_id=tenant_id,
                user_id=user_id,
                data={"entity_count": count},
            )

        return {
            "entity_type": entity_type,
            "tenant_id": str(tenant_id),
            "indexed_count": count,
            "reindexed_at": "now",  # Would use actual timestamp
        }

    def get_search_stats(self, tenant_id: UUID) -> dict[str, Any]:
        """Get search statistics for a tenant.

        Args:
            tenant_id: Tenant ID

        Returns:
            Dictionary with search statistics
        """
        # Get total indexed entities by type
        stats = {}
        
        # This would typically query the search_index table
        # For now, we'll return placeholder data
        # In a real implementation, this would:
        # 1. Count total indexed entities
        # 2. Count by entity type
        # 3. Get last indexing time
        # 4. Get search performance metrics
        
        return {
            "tenant_id": str(tenant_id),
            "total_indexed": 0,
            "indexed_by_type": {},
            "last_indexed": None,
            "search_performance": {
                "avg_search_time_ms": 0,
                "total_searches": 0,
            },
        }

    def bulk_index_entities(
        self,
        tenant_id: UUID,
        entities: list[dict[str, Any]],
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Bulk index multiple entities.

        Args:
            tenant_id: Tenant ID
            entities: List of entities to index
            user_id: User ID performing the action (optional)

        Returns:
            Dictionary with bulk indexing results
        """
        indexed_count = 0
        failed_count = 0
        errors = []

        for entity_data in entities:
            try:
                self.indexer.index_entity(
                    entity_type=entity_data["entity_type"],
                    entity_id=entity_data["entity_id"],
                    tenant_id=tenant_id,
                    title=entity_data["title"],
                    content=entity_data.get("content"),
                    metadata=entity_data.get("metadata"),
                )
                indexed_count += 1
            except Exception as e:
                failed_count += 1
                errors.append({
                    "entity_type": entity_data["entity_type"],
                    "entity_id": str(entity_data["entity_id"]),
                    "error": str(e),
                })

        # Log bulk indexing event
        if self.event_publisher:
            self.event_publisher.publish(
                event_type="search.bulk_indexed",
                entity_type="bulk",
                entity_id=None,
                tenant_id=tenant_id,
                user_id=user_id,
                data={
                    "total_entities": len(entities),
                    "indexed_count": indexed_count,
                    "failed_count": failed_count,
                },
            )

        return {
            "tenant_id": str(tenant_id),
            "total_entities": len(entities),
            "indexed_count": indexed_count,
            "failed_count": failed_count,
            "errors": errors,
            "indexed_at": "now",  # Would use actual timestamp
        }
