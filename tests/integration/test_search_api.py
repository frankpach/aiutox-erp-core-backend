"""Integration tests for Search API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_search(client, test_user, auth_headers, db_session):
    """Test global search."""
    # Assign search.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="search",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First index an entity (requires search.manage)
    manage_role = ModuleRole(
        user_id=test_user.id,
        module="search",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(manage_role)
    db_session.commit()

    entity_id = uuid4()
    index_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "title": "Test Product",
        "content": "This is a test product",
    }
    client.post(
        "/api/v1/search/index",
        json=index_data,
        headers=auth_headers,
    )

    # Now search
    search_data = {"query": "Test", "limit": 10}
    response = client.post(
        "/api/v1/search",
        json=search_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["query"] == "Test"
    assert "results" in data
    assert "total" in data


def test_get_suggestions(client, test_user, auth_headers, db_session):
    """Test getting search suggestions."""
    # Assign search.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="search",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get(
        "/api/v1/search/suggestions?query=test&limit=10",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_index_entity(client, test_user, auth_headers, db_session):
    """Test indexing an entity."""
    # Assign search.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="search",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    entity_id = uuid4()
    index_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "title": "Test Product",
        "content": "Product description",
        "metadata": {"price": 100},
    }

    response = client.post(
        "/api/v1/search/index",
        json=index_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["entity_type"] == "product"
    assert data["entity_id"] == str(entity_id)


def test_remove_index(client, test_user, auth_headers, db_session):
    """Test removing an entity from index."""
    # Assign search.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="search",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First index an entity
    entity_id = uuid4()
    index_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "title": "Test Product",
    }
    client.post(
        "/api/v1/search/index",
        json=index_data,
        headers=auth_headers,
    )

    # Remove it
    response = client.delete(
        f"/api/v1/search/index/product/{entity_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204








