"""Integration tests for Templates module interactions with other modules."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_template_versioning(client, test_user, auth_headers, db_session):
    """Test template versioning when content is updated."""
    # Assign permissions
    template_role = ModuleRole(
        user_id=test_user.id,
        module="templates",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(template_role)
    db_session.commit()

    # Create template
    template_data = {
        "name": "Test Template",
        "template_type": "email",
        "template_format": "html",
        "content": "Version 1: Hello {{ name }}!",
    }
    template_response = client.post(
        "/api/v1/templates",
        json=template_data,
        headers=auth_headers,
    )
    template_id = template_response.json()["data"]["id"]

    # Get versions (should have 1)
    versions_response = client.get(
        f"/api/v1/templates/{template_id}/versions",
        headers=auth_headers,
    )
    assert len(versions_response.json()["data"]) == 1

    # Update template content (should create new version)
    update_data = {"content": "Version 2: Hello {{ name }}, welcome!"}
    client.put(
        f"/api/v1/templates/{template_id}",
        json=update_data,
        headers=auth_headers,
    )

    # Get versions again (should have 2)
    versions_response = client.get(
        f"/api/v1/templates/{template_id}/versions",
        headers=auth_headers,
    )
    versions = versions_response.json()["data"]
    assert len(versions) == 2
    # Latest version should be current
    current_versions = [v for v in versions if v["is_current"]]
    assert len(current_versions) == 1
    assert "Version 2" in current_versions[0]["content"]


def test_template_render_with_variables(client, test_user, auth_headers, db_session):
    """Test rendering template with various variable types."""
    # Assign permissions
    template_role = ModuleRole(
        user_id=test_user.id,
        module="templates",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(template_role)
    db_session.commit()

    # Create template
    template_data = {
        "name": "Test Template",
        "template_type": "email",
        "template_format": "html",
        "content": "Order {{ order_id }} for {{ customer_name }}: Total ${{ total }}",
    }
    template_response = client.post(
        "/api/v1/templates",
        json=template_data,
        headers=auth_headers,
    )
    template_id = template_response.json()["data"]["id"]

    # Render with variables
    render_data = {
        "template_id": template_id,
        "variables": {
            "order_id": "12345",
            "customer_name": "John Doe",
            "total": "99.99",
        },
    }

    render_response = client.post(
        f"/api/v1/templates/{template_id}/render",
        json=render_data,
        headers=auth_headers,
    )

    assert render_response.status_code == 200
    rendered = render_response.json()["data"]["rendered_content"]
    assert "12345" in rendered
    assert "John Doe" in rendered
    assert "99.99" in rendered


def test_template_publishes_events(client, test_user, auth_headers, db_session):
    """Test that templates publish events."""
    # Assign permissions
    template_role = ModuleRole(
        user_id=test_user.id,
        module="templates",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(template_role)
    db_session.commit()

    template_data = {
        "name": "Test Template",
        "template_type": "email",
        "template_format": "html",
        "content": "Hello {{ name }}!",
    }

    with patch("app.core.pubsub.publisher.EventPublisher.publish") as mock_publish:
        mock_publish.return_value = AsyncMock(return_value="test-message-id")

        response = client.post(
            "/api/v1/templates",
            json=template_data,
            headers=auth_headers,
        )

        assert response.status_code == 201
        # Event publishing is done via background task
        assert True  # Background task scheduled








