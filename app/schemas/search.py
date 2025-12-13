"""Search schemas for API requests and responses."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    """Schema for search request."""

    query: str = Field(..., description="Search query", min_length=1)
    entity_types: list[str] | None = Field(None, description="Filter by entity types")
    limit: int = Field(default=50, ge=1, le=100, description="Maximum number of results")


class SearchResult(BaseModel):
    """Schema for a single search result."""

    id: str = Field(..., description="Entity ID")
    title: str = Field(..., description="Entity title")
    content: str | None = Field(None, description="Content preview")
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    """Schema for search response."""

    query: str = Field(..., description="Search query")
    total: int = Field(..., description="Total number of results")
    results: dict[str, list[SearchResult]] = Field(..., description="Results grouped by entity type")

    model_config = ConfigDict(from_attributes=True)


class SearchSuggestion(BaseModel):
    """Schema for search suggestion."""

    text: str = Field(..., description="Suggestion text")
    entity_type: str = Field(..., description="Entity type")
    entity_id: str = Field(..., description="Entity ID")

    model_config = ConfigDict(from_attributes=True)


class IndexEntityRequest(BaseModel):
    """Schema for indexing an entity."""

    entity_type: str = Field(..., description="Entity type", max_length=50)
    entity_id: UUID = Field(..., description="Entity ID")
    title: str = Field(..., description="Entity title", max_length=255)
    content: str | None = Field(None, description="Entity content")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

