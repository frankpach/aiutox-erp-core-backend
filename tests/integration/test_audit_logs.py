"""Integration tests for audit logs functionality."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.repositories.audit_repository import AuditRepository


def test_create_audit_log(db_session: Session, test_user: User) -> None:
    """Test creating an audit log entry."""
    repo = AuditRepository(db_session)

    audit_log = repo.create_audit_log(
        user_id=test_user.id,
        tenant_id=test_user.tenant_id,
        action="test_action",
        resource_type="user",
        resource_id=test_user.id,
        details={"test": "data"},
        ip_address="127.0.0.1",
        user_agent="test-agent",
    )

    assert audit_log.id is not None
    assert audit_log.user_id == test_user.id
    assert audit_log.tenant_id == test_user.tenant_id
    assert audit_log.action == "test_action"
    assert audit_log.resource_type == "user"
    assert audit_log.resource_id == test_user.id
    assert audit_log.details == {"test": "data"}
    assert audit_log.ip_address == "127.0.0.1"
    assert audit_log.user_agent == "test-agent"
    assert audit_log.created_at is not None


def test_get_audit_logs_with_filters(
    db_session: Session, test_user: User
) -> None:
    """Test getting audit logs with various filters."""
    from uuid import uuid4

    repo = AuditRepository(db_session)

    # Create another user in the same tenant
    from app.core.auth import hash_password

    other_user = User(
        email=f"other-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        full_name="Other User",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    # Create multiple audit logs
    repo.create_audit_log(
        user_id=test_user.id,
        tenant_id=test_user.tenant_id,
        action="create_user",
        resource_type="user",
        resource_id=test_user.id,
    )

    repo.create_audit_log(
        user_id=other_user.id,
        tenant_id=other_user.tenant_id,
        action="grant_permission",
        resource_type="permission",
        resource_id=uuid4(),
    )

    repo.create_audit_log(
        user_id=test_user.id,
        tenant_id=test_user.tenant_id,
        action="update_user",
        resource_type="user",
        resource_id=test_user.id,
    )

    # Filter by user_id
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, user_id=test_user.id
    )
    assert total == 2
    assert all(log.user_id == test_user.id for log in logs)

    # Filter by action
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, action="create_user"
    )
    assert total == 1
    assert logs[0].action == "create_user"

    # Filter by resource_type
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, resource_type="permission"
    )
    assert total == 1
    assert logs[0].resource_type == "permission"


def test_get_audit_logs_with_date_filters(
    db_session: Session, test_user: User
) -> None:
    """Test getting audit logs with date filters."""
    repo = AuditRepository(db_session)

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    # Create audit log
    repo.create_audit_log(
        user_id=test_user.id,
        tenant_id=test_user.tenant_id,
        action="test_action",
    )

    # Filter by date_from
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, date_from=yesterday
    )
    assert total >= 1

    # Filter by date_to
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, date_to=tomorrow
    )
    assert total >= 1

    # Filter by date range
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, date_from=yesterday, date_to=tomorrow
    )
    assert total >= 1


def test_get_audit_logs_pagination(
    db_session: Session, test_user: User
) -> None:
    """Test pagination for audit logs."""
    repo = AuditRepository(db_session)

    # Create multiple audit logs
    for i in range(5):
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_user.tenant_id,
            action=f"action_{i}",
        )

    # Get first page
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, skip=0, limit=2
    )
    assert total >= 5
    assert len(logs) == 2

    # Get second page
    logs, total = repo.get_audit_logs(
        tenant_id=test_user.tenant_id, skip=2, limit=2
    )
    assert total >= 5
    assert len(logs) == 2


def test_get_audit_logs_multi_tenant_isolation(
    db_session: Session, test_user: User
) -> None:
    """Test that audit logs are isolated by tenant."""
    repo = AuditRepository(db_session)

    # Create audit log for test_user's tenant
    repo.create_audit_log(
        user_id=test_user.id,
        tenant_id=test_user.tenant_id,
        action="test_action",
    )

    # Create audit log for different tenant
    other_tenant_id = uuid4()
    repo.create_audit_log(
        user_id=test_user.id,
        tenant_id=other_tenant_id,
        action="test_action",
    )

    # Query for test_user's tenant
    logs, total = repo.get_audit_logs(tenant_id=test_user.tenant_id)
    assert total == 1
    assert logs[0].tenant_id == test_user.tenant_id


def test_get_audit_logs_endpoint_with_permission(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Test GET /api/v1/auth/audit-logs endpoint with proper permission."""
    from app.models.user_role import UserRole
    from app.services.auth_service import AuthService

    # Assign admin role to test_user
    admin_role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(admin_role)
    db_session.commit()

    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/auth/audit-logs",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)
    assert "total" in data["meta"]
    assert "page" in data["meta"]
    assert "page_size" in data["meta"]


def test_get_audit_logs_endpoint_without_permission(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Test GET /api/v1/auth/audit-logs endpoint without permission."""
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/auth/audit-logs",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403
    data = response.json()
    assert "error" in data["detail"]
    assert data["detail"]["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


def test_get_audit_logs_endpoint_with_filters(
    client: TestClient, db_session: Session, test_user: User
) -> None:
    """Test GET /api/v1/auth/audit-logs endpoint with filters."""
    from app.models.user_role import UserRole
    from app.services.auth_service import AuthService

    # Assign admin role to test_user
    admin_role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(admin_role)
    db_session.commit()

    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    response = client.get(
        "/api/v1/auth/audit-logs",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "user_id": str(test_user.id),
            "action": "create_user",
            "page": 1,
            "page_size": 20,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data


def test_audit_log_created_on_permission_grant(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    """Test that audit log is created when granting permission."""
    from app.core.auth import hash_password
    from app.models.module_role import ModuleRole
    from app.repositories.audit_repository import AuditRepository
    from app.services.auth_service import AuthService
    from uuid import uuid4

    # Make test_user a leader of inventory module
    module_role = ModuleRole(
        user_id=test_user.id,
        module="inventory",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create target user
    target_user = User(
        email=f"target-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        full_name="Target User",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    db_session.add(target_user)
    db_session.commit()

    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)

    repo = AuditRepository(db_session)
    initial_count = repo.get_audit_logs(tenant_id=test_user.tenant_id)[1]

    # Grant permission
    response = client.post(
        "/api/v1/auth/modules/inventory/permissions",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "user_id": str(target_user.id),
            "permission": "inventory.view",
        },
    )

    assert response.status_code == 201

    # Check that audit log was created
    logs, total = repo.get_audit_logs(tenant_id=test_user.tenant_id)
    assert total > initial_count

    # Find the grant_permission log
    grant_logs = [
        log
        for log in logs
        if log.action == "grant_delegated_permission"
        and log.user_id == test_user.id
    ]
    assert len(grant_logs) > 0


def test_audit_log_created_on_role_assignment(
    client: TestClient,
    db_session: Session,
    test_user: User,
) -> None:
    """Test that audit log is created when assigning role."""
    from app.core.auth import hash_password
    from app.models.user_role import UserRole
    from app.repositories.audit_repository import AuditRepository
    from app.services.auth_service import AuthService
    from uuid import uuid4

    # Create admin user
    admin_user = User(
        email=f"admin-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        full_name="Admin User",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    admin_role = UserRole(
        user_id=admin_user.id,
        role="admin",
        granted_by=admin_user.id,
    )
    db_session.add(admin_role)
    db_session.commit()

    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(admin_user)

    repo = AuditRepository(db_session)
    initial_count = repo.get_audit_logs(tenant_id=test_user.tenant_id)[1]

    # Assign role
    response = client.post(
        f"/api/v1/auth/roles/{test_user.id}",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"role": "viewer"},
    )

    assert response.status_code == 201  # Created

    # Check that audit log was created
    logs, total = repo.get_audit_logs(tenant_id=test_user.tenant_id)
    assert total > initial_count

    # Find the assign_global_role log
    assign_logs = [
        log
        for log in logs
        if log.action == "assign_global_role" and log.user_id == admin_user.id
    ]
    assert len(assign_logs) > 0


def test_audit_log_created_on_user_creation(
    client: TestClient,
    db_session: Session,
    test_user: User,
    test_tenant,
) -> None:
    """Test that audit log is created when creating user."""
    from app.core.auth import hash_password
    from app.models.user_role import UserRole
    from app.repositories.audit_repository import AuditRepository
    from app.services.auth_service import AuthService
    from uuid import uuid4

    # Create admin user
    admin_user = User(
        email=f"admin-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("password123"),
        full_name="Admin User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)

    admin_role = UserRole(
        user_id=admin_user.id,
        role="admin",
        granted_by=admin_user.id,
    )
    db_session.add(admin_role)
    db_session.commit()

    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(admin_user)

    repo = AuditRepository(db_session)
    initial_count = repo.get_audit_logs(tenant_id=test_tenant.id)[1]

    # Create user
    response = client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "email": f"newuser-{uuid4().hex[:8]}@example.com",
            "password": "SecurePass123!",
            "full_name": "New User",
            "tenant_id": str(test_tenant.id),
        },
    )

    assert response.status_code == 201

    # Check that audit log was created
    logs, total = repo.get_audit_logs(tenant_id=test_tenant.id)
    assert total > initial_count

    # Find the create_user log
    create_logs = [
        log
        for log in logs
        if log.action == "create_user" and log.user_id == admin_user.id
    ]
    assert len(create_logs) > 0

