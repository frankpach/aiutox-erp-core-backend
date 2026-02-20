"""Security-focused integration tests for Integrations Webhooks API endpoints."""

from uuid import uuid4

import pytest

from app.core.auth import hash_password
from app.models.user import User
from tests.helpers import create_user_with_permission


def _assert_api_error_code(response, expected_code: str) -> None:
    payload = response.json()
    if "error" in payload:
        assert payload["error"]["code"] == expected_code
        return
    if "detail" in payload and isinstance(payload["detail"], dict):
        assert payload["detail"]["error"]["code"] == expected_code
        return
    raise AssertionError("API error code not found in response payload")


@pytest.mark.integration
@pytest.mark.security
def test_webhooks_list_requires_auth(client_with_db):
    """Ensure unauthenticated users cannot list webhooks."""
    response = client_with_db.get("/api/v1/integrations/webhooks")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_webhooks_list_requires_view_permission(client_with_db, auth_headers):
    """Ensure integrations.view permission is required to list webhooks."""
    response = client_with_db.get(
        "/api/v1/integrations/webhooks",
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_webhooks_events_requires_view_permission(client_with_db, auth_headers):
    """Ensure integrations.view permission is required to list webhook events."""
    response = client_with_db.get(
        "/api/v1/integrations/webhooks/events",
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_webhooks_create_requires_manage_permission(
    client_with_db, module_role_headers
):
    """Ensure integrations.manage permission is required to create webhooks."""
    viewer_headers = module_role_headers("integrations", "viewer")
    response = client_with_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "event_type": "task.created",
        },
        headers=viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_webhooks_update_and_delete_require_manage_permission(
    client_with_db, module_role_headers, db_session, test_tenant
):
    """Ensure integrations.manage permission is required to update/delete webhooks."""
    manager_headers = module_role_headers("integrations", "manager")

    viewer_user = User(
        email=f"viewer-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test_password_123"),
        full_name="Viewer User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(viewer_user)
    db_session.commit()
    db_session.refresh(viewer_user)

    viewer_headers = create_user_with_permission(
        db_session, viewer_user, "integrations", "viewer"
    )

    create_response = client_with_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "Webhook Update",
            "url": "https://example.com/webhook-update",
            "event_type": "task.updated",
        },
        headers=manager_headers,
    )
    assert create_response.status_code == 201
    webhook_id = create_response.json()["data"]["id"]

    update_response = client_with_db.put(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        json={
            "name": "Webhook Update",
            "config": {
                "url": "https://example.com/updated",
                "event_type": "task.updated",
            },
            "status": "active",
        },
        headers=viewer_headers,
    )
    assert update_response.status_code == 403
    _assert_api_error_code(update_response, "AUTH_INSUFFICIENT_PERMISSIONS")

    delete_response = client_with_db.delete(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=viewer_headers,
    )
    assert delete_response.status_code == 403
    _assert_api_error_code(delete_response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_webhooks_get_requires_view_permission(
    client_with_db, module_role_headers, db_session, test_tenant
):
    """Ensure integrations.view permission is required to get a webhook."""
    manager_headers = module_role_headers("integrations", "manager")

    viewer_user = User(
        email=f"viewer-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test_password_123"),
        full_name="Viewer User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(viewer_user)
    db_session.commit()
    db_session.refresh(viewer_user)

    viewer_headers = create_user_with_permission(
        db_session, viewer_user, "integrations", "viewer"
    )

    create_response = client_with_db.post(
        "/api/v1/integrations/webhooks",
        json={
            "name": "Webhook Get",
            "url": "https://example.com/webhook-get",
            "event_type": "task.created",
        },
        headers=manager_headers,
    )
    assert create_response.status_code == 201
    webhook_id = create_response.json()["data"]["id"]

    get_response = client_with_db.get(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=viewer_headers,
    )
    assert get_response.status_code == 200
    payload = get_response.json()
    assert payload["data"]["id"] == webhook_id
