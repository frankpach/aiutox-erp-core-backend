"""Integration tests for Automation API endpoints."""

import pytest
from uuid import uuid4

from app.models.automation import Rule
from app.models.module_role import ModuleRole


def test_create_rule(client, test_user, auth_headers, db_session):
    """Test creating an automation rule."""
    # Assign automation.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="automation",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    rule_data = {
        "name": "Test Rule",
        "description": "Test automation rule",
        "enabled": True,
        "trigger": {"type": "event", "event_type": "product.created"},
        "conditions": [
            {"field": "metadata.stock.quantity", "operator": "<", "value": 10}
        ],
        "actions": [
            {
                "type": "notification",
                "template": "low_stock_alert",
                "recipients": ["admin@tenant.com"],
            }
        ],
    }

    response = client.post(
        "/api/v1/automation/rules",
        json=rule_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Rule"
    assert data["enabled"] is True
    assert "id" in data


def test_list_rules(client, test_user, auth_headers, db_session):
    """Test listing automation rules."""
    # Assign automation.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="automation",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    from app.repositories.automation_repository import AutomationRepository

    repo = AutomationRepository(db_session)
    repo.create_rule(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Rule 1",
            "enabled": True,
            "trigger": {"type": "event", "event_type": "product.created"},
            "actions": [{"type": "notification", "template": "test"}],
        }
    )

    response = client.get("/api/v1/automation/rules", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0


def test_get_rule(client, test_user, auth_headers, db_session):
    """Test getting a specific rule."""
    # Assign automation.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="automation",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    from app.repositories.automation_repository import AutomationRepository

    repo = AutomationRepository(db_session)
    rule = repo.create_rule(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Rule",
            "enabled": True,
            "trigger": {"type": "event", "event_type": "product.created"},
            "actions": [{"type": "notification", "template": "test"}],
        }
    )

    response = client.get(
        f"/api/v1/automation/rules/{rule.id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(rule.id)
    assert data["name"] == "Test Rule"


def test_update_rule(client, test_user, auth_headers, db_session):
    """Test updating a rule."""
    # Assign automation.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="automation",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    from app.repositories.automation_repository import AutomationRepository

    repo = AutomationRepository(db_session)
    rule = repo.create_rule(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Rule",
            "enabled": True,
            "trigger": {"type": "event", "event_type": "product.created"},
            "actions": [{"type": "notification", "template": "test"}],
        }
    )

    update_data = {"name": "Updated Rule", "enabled": False}

    response = client.put(
        f"/api/v1/automation/rules/{rule.id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Rule"
    assert data["enabled"] is False


def test_delete_rule(client, test_user, auth_headers, db_session):
    """Test deleting a rule."""
    # Assign automation.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="automation",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    from app.repositories.automation_repository import AutomationRepository

    repo = AutomationRepository(db_session)
    rule = repo.create_rule(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Rule",
            "enabled": True,
            "trigger": {"type": "event", "event_type": "product.created"},
            "actions": [{"type": "notification", "template": "test"}],
        }
    )

    response = client.delete(
        f"/api/v1/automation/rules/{rule.id}", headers=auth_headers
    )

    assert response.status_code == 204

    # Verify rule is deleted
    get_response = client.get(
        f"/api/v1/automation/rules/{rule.id}", headers=auth_headers
    )
    assert get_response.status_code == 404

