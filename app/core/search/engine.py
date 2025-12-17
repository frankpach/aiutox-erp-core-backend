"""Search engine for global search functionality."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.search_index import SearchIndex
from app.repositories.search_repository import SearchRepository

logger = logging.getLogger(__name__)


class SearchEngine:
    """Engine for global search across all entities."""

    def __init__(self, db: Session):
        """Initialize search engine.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = SearchRepository(db)

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
        results = self.repository.search(tenant_id, query, entity_types, limit)

        # Group results by entity type
        categorized_results: dict[str, list[dict[str, Any]]] = {}
        for result in results:
            entity_type = result.entity_type
            if entity_type not in categorized_results:
                categorized_results[entity_type] = []

            categorized_results[entity_type].append(
                {
                    "id": str(result.entity_id),
                    "title": result.title,
                    "content": result.content[:200] if result.content else None,  # Preview
                    "entity_type": entity_type,
                    "entity_id": str(result.entity_id),
                }
            )

        return {
            "query": query,
            "total": len(results),
            "results": categorized_results,
        }

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
        results = self.repository.search(tenant_id, query, None, limit)

        suggestions = []
        for result in results[:limit]:
            suggestions.append(
                {
                    "text": result.title,
                    "entity_type": result.entity_type,
                    "entity_id": str(result.entity_id),
                }
            )

        return suggestions







