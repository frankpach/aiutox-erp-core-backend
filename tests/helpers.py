"""Helper functions for tests."""

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.models.module_role import ModuleRole
from app.models.task import Task
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import AuthService


def create_user_with_permission(
    db_session: Session,
    user: User,
    module: str,
    role_name: str = "manager",
) -> dict[str, str]:
    """
    Create a module role for a user and return updated auth headers.

    Args:
        db_session: Database session.
        user: User object.
        module: Module name (e.g., "tasks", "files").
        role_name: Role name (e.g., "manager", "viewer", "editor").

    Returns:
        Dictionary with Authorization header containing updated token.
    """
    # Assign permission
    module_role = ModuleRole(
        user_id=user.id,
        module=module,
        role_name=role_name,
        granted_by=user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(user)

    # Create token with updated permissions
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(user)
    return {"Authorization": f"Bearer {access_token}"}


def create_user_with_system_permission(
    db_session: Session,
    user: User,
    role: str = "admin",
) -> dict[str, str]:
    """
    Create a system role for a user and return updated auth headers.

    Args:
        db_session: Database session.
        user: User object.
        role: System role name (e.g., "admin", "owner", "manager").

    Returns:
        Dictionary with Authorization header containing updated token.
    """
    # Assign system role
    user_role = UserRole(
        user_id=user.id,
        role=role,
        granted_by=user.id,
    )
    db_session.add(user_role)
    db_session.commit()
    db_session.refresh(user)

    # Create token with updated permissions
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(user)
    return {"Authorization": f"Bearer {access_token}"}


def create_auth_headers_for_user(db_session: Session, user: User) -> dict[str, str]:
    """Create auth headers for an existing user."""
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(user)
    return {"Authorization": f"Bearer {access_token}"}


def create_tenant_with_user(
    db_session: Session,
    email: str | None = None,
    full_name: str = "Test User",
    password: str = "test_password_123",
) -> tuple[Tenant, User]:
    """Create a tenant with a user for tenant-isolation tests."""
    tenant = Tenant(
        name=f"Test Tenant {uuid4().hex[:6]}",
        slug=f"test-tenant-{uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.flush()
    db_session.refresh(tenant)

    user = User(
        email=email or f"test-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(password),
        full_name=full_name,
        tenant_id=tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return tenant, user


def create_task(
    db_session: Session,
    tenant_id: UUID,
    created_by_id: UUID,
    title: str | None = None,
    description: str | None = None,
    status: str = "todo",
    priority: str = "medium",
    assigned_to_id: UUID | None = None,
    due_date: datetime | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    all_day: bool = False,
    metadata: dict[str, Any] | None = None,
) -> Task:
    """Create a task for tests with minimal defaults."""
    task = Task(
        id=uuid4(),
        tenant_id=tenant_id,
        title=title or f"Test Task {uuid4().hex[:6]}",
        description=description or "Test task description",
        status=status,
        priority=priority,
        assigned_to_id=assigned_to_id,
        created_by_id=created_by_id,
        due_date=due_date,
        start_at=start_at,
        end_at=end_at,
        all_day=all_day,
        task_metadata=metadata,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def parse_sse_events(lines: Iterable[str]) -> list[dict[str, Any]]:
    """Parse SSE lines into a list of event payloads."""
    events: list[dict[str, Any]] = []
    current: dict[str, Any] = {}

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current:
                events.append(current)
                current = {}
            continue
        if line.startswith("event:"):
            current["event"] = line.split("event:", 1)[1].strip()
            continue
        if line.startswith("data:"):
            data_text = line.split("data:", 1)[1].strip()
            try:
                current["data"] = json.loads(data_text)
            except json.JSONDecodeError:
                current["data"] = data_text

    if current:
        events.append(current)

    return events
