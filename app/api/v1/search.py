"""Search router for global search functionality."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.core.search.engine import SearchEngine
from app.core.search.indexer import SearchIndexer
from app.models.user import User
from app.schemas.common import StandardResponse
from app.schemas.search import (
    IndexEntityRequest,
    SearchRequest,
    SearchResponse,
    SearchSuggestion,
)

router = APIRouter()


def get_search_engine(db: Annotated[Session, Depends(get_db)]) -> SearchEngine:
    """Dependency to get SearchEngine."""
    return SearchEngine(db)


def get_search_indexer(db: Annotated[Session, Depends(get_db)]) -> SearchIndexer:
    """Dependency to get SearchIndexer."""
    return SearchIndexer(db)


@router.post(
    "",
    response_model=StandardResponse[SearchResponse],
    status_code=status.HTTP_200_OK,
    summary="Global search",
    description="Search across all indexed entities. Requires search.view permission.",
)
async def search(
    search_request: SearchRequest,
    current_user: Annotated[User, Depends(require_permission("search.view"))],
    engine: Annotated[SearchEngine, Depends(get_search_engine)],
) -> StandardResponse[SearchResponse]:
    """Search across all indexed entities."""
    results = engine.search(
        tenant_id=current_user.tenant_id,
        query=search_request.query,
        entity_types=search_request.entity_types,
        limit=search_request.limit,
    )

    return StandardResponse(
        data=SearchResponse.model_validate(results),
        message="Search completed successfully",
    )


@router.get(
    "/suggestions",
    response_model=StandardResponse[list[SearchSuggestion]],
    status_code=status.HTTP_200_OK,
    summary="Get search suggestions",
    description="Get search suggestions. Requires search.view permission.",
)
async def get_suggestions(
    query: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of suggestions"),
    current_user: Annotated[User, Depends(require_permission("search.view"))],
    engine: Annotated[SearchEngine, Depends(get_search_engine)],
) -> StandardResponse[list[SearchSuggestion]]:
    """Get search suggestions."""
    suggestions = engine.get_suggestions(
        tenant_id=current_user.tenant_id,
        query=query,
        limit=limit,
    )

    return StandardResponse(
        data=[SearchSuggestion.model_validate(s) for s in suggestions],
        message="Suggestions retrieved successfully",
    )


@router.post(
    "/index",
    status_code=status.HTTP_201_CREATED,
    summary="Index entity",
    description="Index an entity for search. Requires search.manage permission.",
)
async def index_entity(
    index_request: IndexEntityRequest,
    current_user: Annotated[User, Depends(require_permission("search.manage"))],
    indexer: Annotated[SearchIndexer, Depends(get_search_indexer)],
) -> StandardResponse[dict]:
    """Index an entity for search."""
    index = indexer.index_entity(
        entity_type=index_request.entity_type,
        entity_id=index_request.entity_id,
        tenant_id=current_user.tenant_id,
        title=index_request.title,
        content=index_request.content,
        metadata=index_request.metadata,
    )

    return StandardResponse(
        data={"id": str(index.id), "entity_type": index.entity_type, "entity_id": str(index.entity_id)},
        message="Entity indexed successfully",
    )


@router.delete(
    "/index/{entity_type}/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove entity from index",
    description="Remove an entity from search index. Requires search.manage permission.",
)
async def remove_index(
    entity_type: str = Path(..., description="Entity type"),
    entity_id: UUID = Path(..., description="Entity ID"),
    current_user: Annotated[User, Depends(require_permission("search.manage"))],
    indexer: Annotated[SearchIndexer, Depends(get_search_indexer)],
) -> None:
    """Remove an entity from search index."""
    deleted = indexer.remove_index(entity_type, entity_id, current_user.tenant_id)
    if not deleted:
        from app.core.exceptions import APIException

        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="INDEX_NOT_FOUND",
            message=f"Index for {entity_type}:{entity_id} not found",
        )

