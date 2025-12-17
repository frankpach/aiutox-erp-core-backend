"""Unit tests for TagService."""

import pytest
from uuid import uuid4

from app.core.tags.service import TagService


@pytest.fixture
def tag_service(db_session):
    """Create TagService instance."""
    return TagService(db=db_session)


def test_create_tag(tag_service, test_tenant):
    """Test creating a tag."""
    tag = tag_service.create_tag(
        name="Important",
        tenant_id=test_tenant.id,
        color="#FF5733",
        description="Important items",
    )

    assert tag.name == "Important"
    assert tag.color == "#FF5733"
    assert tag.description == "Important items"
    assert tag.tenant_id == test_tenant.id
    assert tag.is_active is True


def test_get_tag(tag_service, test_tenant):
    """Test getting a tag."""
    # Create a tag first
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_tenant.id,
    )

    # Get it
    retrieved = tag_service.get_tag(tag.id, test_tenant.id)

    assert retrieved is not None
    assert retrieved.id == tag.id
    assert retrieved.name == "Test Tag"


def test_get_all_tags(tag_service, test_tenant):
    """Test getting all tags."""
    # Create multiple tags
    tag1 = tag_service.create_tag(
        name="Tag 1",
        tenant_id=test_tenant.id,
    )
    tag2 = tag_service.create_tag(
        name="Tag 2",
        tenant_id=test_tenant.id,
    )

    # Get all tags
    tags = tag_service.get_all_tags(test_tenant.id)

    assert len(tags) >= 2
    assert any(t.id == tag1.id for t in tags)
    assert any(t.id == tag2.id for t in tags)


def test_search_tags(tag_service, test_tenant):
    """Test searching tags."""
    # Create tags
    tag1 = tag_service.create_tag(
        name="Important",
        tenant_id=test_tenant.id,
    )
    tag_service.create_tag(
        name="Regular",
        tenant_id=test_tenant.id,
    )

    # Search for "Important"
    results = tag_service.search_tags(test_tenant.id, "Important")

    assert len(results) >= 1
    assert any(t.id == tag1.id for t in results)


def test_update_tag(tag_service, test_tenant):
    """Test updating a tag."""
    # Create a tag
    tag = tag_service.create_tag(
        name="Original Name",
        tenant_id=test_tenant.id,
        color="#000000",
    )

    # Update it
    updated = tag_service.update_tag(
        tag.id,
        test_tenant.id,
        name="Updated Name",
        color="#FFFFFF",
    )

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.color == "#FFFFFF"


def test_delete_tag(tag_service, test_tenant):
    """Test deleting a tag (soft delete)."""
    # Create a tag
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_tenant.id,
    )

    # Delete it
    deleted = tag_service.delete_tag(tag.id, test_tenant.id)

    assert deleted is True

    # Verify it's soft deleted (is_active = False)
    retrieved = tag_service.get_tag(tag.id, test_tenant.id)
    assert retrieved is None  # get_tag filters by is_active=True


def test_add_tag_to_entity(tag_service, test_tenant):
    """Test adding a tag to an entity."""
    # Create a tag
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_tenant.id,
    )

    entity_id = uuid4()

    # Add tag to entity
    entity_tag = tag_service.add_tag_to_entity(
        tag_id=tag.id,
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    assert entity_tag.tag_id == tag.id
    assert entity_tag.entity_type == "product"
    assert entity_tag.entity_id == entity_id


def test_add_tag_to_entity_duplicate(tag_service, test_tenant):
    """Test adding duplicate tag to entity raises error."""
    # Create a tag
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_tenant.id,
    )

    entity_id = uuid4()

    # Add tag first time
    tag_service.add_tag_to_entity(
        tag_id=tag.id,
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    # Try to add again (should raise error)
    with pytest.raises(ValueError, match="already has tag"):
        tag_service.add_tag_to_entity(
            tag_id=tag.id,
            entity_type="product",
            entity_id=entity_id,
            tenant_id=test_tenant.id,
        )


def test_remove_tag_from_entity(tag_service, test_tenant):
    """Test removing a tag from an entity."""
    # Create a tag
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_tenant.id,
    )

    entity_id = uuid4()

    # Add tag to entity
    tag_service.add_tag_to_entity(
        tag_id=tag.id,
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    # Remove it
    removed = tag_service.remove_tag_from_entity(
        tag_id=tag.id,
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    assert removed is True

    # Verify it's removed
    entity_tags = tag_service.get_entity_tags(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )
    assert not any(et.id == tag.id for et in entity_tags)


def test_get_entity_tags(tag_service, test_tenant):
    """Test getting tags for an entity."""
    # Create tags
    tag1 = tag_service.create_tag(
        name="Tag 1",
        tenant_id=test_tenant.id,
    )
    tag2 = tag_service.create_tag(
        name="Tag 2",
        tenant_id=test_tenant.id,
    )

    entity_id = uuid4()

    # Add tags to entity
    tag_service.add_tag_to_entity(
        tag_id=tag1.id,
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )
    tag_service.add_tag_to_entity(
        tag_id=tag2.id,
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    # Get entity tags
    entity_tags = tag_service.get_entity_tags(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=test_tenant.id,
    )

    assert len(entity_tags) >= 2
    tag_ids = [et.id for et in entity_tags]
    assert tag1.id in tag_ids
    assert tag2.id in tag_ids







