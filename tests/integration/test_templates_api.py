"""Integration tests for Templates API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_template(client, test_user, auth_headers, db_session):
    """Test creating a template."""
    # Assign templates.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="templates",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    template_data = {
        "name": "Test Template",
        "template_type": "email",
        "template_format": "html",
        "content": "Hello {{ name }}!",
    }

    response = client.post(
        "/api/v1/templates",
        json=template_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Template"
    assert data["template_type"] == "email"
    assert "id" in data


def test_render_template(client, test_user, auth_headers, db_session):
    """Test rendering a template."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="templates",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First create a template
    template_data = {
        "name": "Test Template",
        "template_type": "email",
        "template_format": "html",
        "content": "Hello {{ name }}, your order {{ order_id }} is ready!",
    }
    template_response = client.post(
        "/api/v1/templates",
        json=template_data,
        headers=auth_headers,
    )
    template_id = template_response.json()["data"]["id"]

    # Render template
    render_data = {
        "template_id": template_id,
        "variables": {"name": "John", "order_id": "12345"},
    }

    response = client.post(
        f"/api/v1/templates/{template_id}/render",
        json=render_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "rendered_content" in data
    assert "Hello John, your order 12345 is ready!" in data["rendered_content"]








