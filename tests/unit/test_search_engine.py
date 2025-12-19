"""Unit tests for SearchEngine."""

import pytest
from uuid import uuid4

from app.core.search.engine import SearchEngine
from app.core.search.indexer import SearchIndexer


@pytest.fixture
def search_engine(db_session):
    """Create SearchEngine instance."""
    return SearchEngine(db=db_session)


@pytest.fixture
def search_indexer(db_session):
    """Create SearchIndexer instance."""
    return SearchIndexer(db=db_session)


def test_index_entity(search_indexer, test_tenant):
    """Test indexing an entity."""
    entity_id = uuid4()
    index = search_indexer.index_entity(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        title="Test Product",
        content="This is a test product description",
        metadata={"price": 100, "category": "electronics"},
    )

    assert index.entity_type == "product"
    assert index.entity_id == entity_id
    assert index.title == "Test Product"
    assert index.content == "This is a test product description"
    assert index.tenant_id == test_tenant.id


def test_index_entity_update(search_indexer, test_tenant):
    """Test updating an existing index."""
    entity_id = uuid4()

    # Create initial index
    index1 = search_indexer.index_entity(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        title="Original Title",
        content="Original content",
    )

    # Update it
    index2 = search_indexer.index_entity(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        title="Updated Title",
        content="Updated content",
    )

    assert index2.id == index1.id  # Same index updated
    assert index2.title == "Updated Title"
    assert index2.content == "Updated content"


def test_remove_index(search_indexer, test_tenant):
    """Test removing an entity from index."""
    entity_id = uuid4()

    # Index an entity
    index = search_indexer.index_entity(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        title="Test Product",
    )

    # Remove it
    deleted = search_indexer.remove_index("product", entity_id, test_tenant.id)

    assert deleted is True

    # Verify it's removed
    index_after = search_indexer.repository.get_index_by_entity(
        "product", entity_id, test_tenant.id
    )
    assert index_after is None


def test_search(search_engine, search_indexer, test_tenant):
    """Test searching across indexed entities."""
    # Index some entities
    entity1_id = uuid4()
    search_indexer.index_entity(
        entity_type="product",
        entity_id=entity1_id,
        tenant_id=test_tenant.id,
        title="Laptop Computer",
        content="High performance laptop for professionals",
    )

    entity2_id = uuid4()
    search_indexer.index_entity(
        entity_type="product",
        entity_id=entity2_id,
        tenant_id=test_tenant.id,
        title="Desktop Computer",
        content="Powerful desktop for gaming",
    )

    # Search
    results = search_engine.search(
        tenant_id=test_tenant.id,
        query="Computer",
        limit=10,
    )

    assert results["query"] == "Computer"
    assert results["total"] >= 2
    assert "product" in results["results"]
    assert len(results["results"]["product"]) >= 2


def test_search_with_entity_type_filter(search_engine, search_indexer, test_tenant):
    """Test searching with entity type filter."""
    # Index different entity types
    product_id = uuid4()
    search_indexer.index_entity(
        entity_type="product",
        entity_id=product_id,
        tenant_id=test_tenant.id,
        title="Test Product",
        content="Product description",
    )

    contact_id = uuid4()
    search_indexer.index_entity(
        entity_type="contact",
        entity_id=contact_id,
        tenant_id=test_tenant.id,
        title="Test Contact",
        content="Contact information",
    )

    # Search only products
    results = search_engine.search(
        tenant_id=test_tenant.id,
        query="Test",
        entity_types=["product"],
        limit=10,
    )

    assert "product" in results["results"]
    assert "contact" not in results["results"]


def test_get_suggestions(search_engine, search_indexer, test_tenant):
    """Test getting search suggestions."""
    # Index some entities
    entity_id = uuid4()
    search_indexer.index_entity(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
        title="Laptop Computer",
        content="High performance laptop",
    )

    # Get suggestions
    suggestions = search_engine.get_suggestions(
        tenant_id=test_tenant.id,
        query="Lap",
        limit=10,
    )

    assert len(suggestions) >= 1
    assert any(s["text"] == "Laptop Computer" for s in suggestions)
    assert all("entity_type" in s for s in suggestions)
    assert all("entity_id" in s for s in suggestions)








