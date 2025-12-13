"""Integration tests for security and multi-tenancy across Fase 3 modules."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole
from app.models.tenant import Tenant
from app.models.user import User
from app.core.auth import hash_password


@pytest.fixture
def second_tenant(db_session):
    """Create a second tenant for multi-tenancy tests."""
    tenant = Tenant(
        id=uuid4(),
        name="Second Tenant",
        slug="second-tenant",
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def second_user(db_session, second_tenant):
    """Create a user in second tenant."""
    user = User(
        id=uuid4(),
        username="second_user",
        email="second@test.com",
        tenant_id=second_tenant.id,
        hashed_password=hash_password("password"),
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_calendar_tenant_isolation(client, test_user, second_user, db_session):
    """Test that calendars are isolated by tenant."""
    # Assign permissions to both users
    role1 = ModuleRole(
        user_id=test_user.id,
        module="calendar",
        role_name="manager",
        granted_by=test_user.id,
    )
    role2 = ModuleRole(
        user_id=second_user.id,
        module="calendar",
        role_name="manager",
        granted_by=second_user.id,
    )
    db_session.add(role1)
    db_session.add(role2)
    db_session.commit()

    # Create calendar for first user
    from app.core.calendar.service import CalendarService
    calendar_service = CalendarService(db_session)

    calendar1 = calendar_service.create_calendar(
        calendar_data={"name": "Tenant 1 Calendar", "calendar_type": "user"},
        tenant_id=test_user.tenant_id,
        owner_id=test_user.id,
    )

    # Try to access from second tenant (should not find it)
    calendar2 = calendar_service.get_calendar(calendar1.id, second_user.tenant_id)
    assert calendar2 is None  # Should not be accessible from different tenant


def test_comments_tenant_isolation(client, test_user, second_user, db_session):
    """Test that comments are isolated by tenant."""
    # Assign permissions
    role1 = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="creator",
        granted_by=test_user.id,
    )
    role2 = ModuleRole(
        user_id=second_user.id,
        module="comments",
        role_name="creator",
        granted_by=second_user.id,
    )
    db_session.add(role1)
    db_session.add(role2)
    db_session.commit()

    entity_id = uuid4()

    # Create comment in first tenant
    from app.core.comments.service import CommentService
    comment_service = CommentService(db_session)

    comment1 = comment_service.create_comment(
        comment_data={
            "entity_type": "product",
            "entity_id": entity_id,
            "content": "Tenant 1 comment",
        },
        tenant_id=test_user.tenant_id,
        user_id=test_user.id,
    )

    # Try to get from second tenant (should not find it)
    comments2 = comment_service.get_comments_by_entity(
        entity_type="product",
        entity_id=entity_id,
        tenant_id=second_user.tenant_id,
    )
    assert len(comments2) == 0  # Should be empty for different tenant


def test_approvals_tenant_isolation(client, test_user, second_user, db_session):
    """Test that approvals are isolated by tenant."""
    # Assign permissions
    role1 = ModuleRole(
        user_id=test_user.id,
        module="approvals",
        role_name="manager",
        granted_by=test_user.id,
    )
    role2 = ModuleRole(
        user_id=second_user.id,
        module="approvals",
        role_name="manager",
        granted_by=second_user.id,
    )
    db_session.add(role1)
    db_session.add(role2)
    db_session.commit()

    # Create flow in first tenant
    from app.core.approvals.service import ApprovalService
    approval_service = ApprovalService(db_session)

    flow1 = approval_service.create_approval_flow(
        flow_data={
            "name": "Tenant 1 Flow",
            "flow_type": "sequential",
            "module": "orders",
        },
        tenant_id=test_user.tenant_id,
        user_id=test_user.id,
    )

    # Try to access from second tenant (should not find it)
    flow2 = approval_service.get_approval_flow(flow1.id, second_user.tenant_id)
    assert flow2 is None  # Should not be accessible from different tenant


def test_permission_required_for_operations(client, test_user, auth_headers, db_session):
    """Test that operations require proper permissions."""
    # Try to create calendar without permission
    calendar_data = {"name": "Test Calendar", "calendar_type": "user"}

    response = client.post(
        "/api/v1/calendar/calendars",
        json=calendar_data,
        headers=auth_headers,
    )

    # Should fail without permission
    assert response.status_code == 403

    # Assign permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="calendar",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Now should succeed
    response = client.post(
        "/api/v1/calendar/calendars",
        json=calendar_data,
        headers=auth_headers,
    )

    assert response.status_code == 201

