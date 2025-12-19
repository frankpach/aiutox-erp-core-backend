"""Unit tests for AuditRepository."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.repositories.audit_repository import AuditRepository


class TestAuditRepository:
    """Test suite for AuditRepository."""

    def test_create_audit_log(self, db_session, test_user, test_tenant):
        """Test creating an audit log entry."""
        repo = AuditRepository(db_session)
        audit_log = repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="create_user",
            resource_type="user",
            resource_id=test_user.id,
            details={"email": test_user.email},
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert audit_log.id is not None
        assert audit_log.user_id == test_user.id
        assert audit_log.tenant_id == test_tenant.id
        assert audit_log.action == "create_user"
        assert audit_log.resource_type == "user"
        assert audit_log.resource_id == test_user.id
        assert audit_log.details == {"email": test_user.email}
        assert audit_log.ip_address == "127.0.0.1"
        assert audit_log.user_agent == "test-agent"

    def test_create_audit_log_system_action(self, db_session, test_tenant):
        """Test creating an audit log for a system action (no user_id)."""
        repo = AuditRepository(db_session)
        audit_log = repo.create_audit_log(
            user_id=None,
            tenant_id=test_tenant.id,
            action="system_maintenance",
            resource_type=None,
            resource_id=None,
        )

        assert audit_log.user_id is None
        assert audit_log.tenant_id == test_tenant.id
        assert audit_log.action == "system_maintenance"

    def test_get_audit_logs_basic(self, db_session, test_user, test_tenant):
        """Test getting audit logs with basic query."""
        repo = AuditRepository(db_session)

        # Create multiple audit logs
        for i in range(3):
            repo.create_audit_log(
                user_id=test_user.id,
                tenant_id=test_tenant.id,
                action=f"action_{i}",
                resource_type="user",
            )

        logs, total = repo.get_audit_logs(tenant_id=test_tenant.id)

        assert total >= 3
        assert len(logs) >= 3

    def test_get_audit_logs_with_filters(self, db_session, test_user, test_tenant):
        """Test getting audit logs with multiple filters."""
        repo = AuditRepository(db_session)

        # Create logs with different actions
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="create_user",
            resource_type="user",
        )
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="update_user",
            resource_type="user",
        )
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="create_user",
            resource_type="permission",
        )

        # Filter by action
        logs, total = repo.get_audit_logs(
            tenant_id=test_tenant.id, action="create_user"
        )

        assert total >= 2
        assert all(log.action == "create_user" for log in logs)

        # Filter by resource_type
        logs, total = repo.get_audit_logs(
            tenant_id=test_tenant.id, resource_type="user"
        )

        assert total >= 2
        assert all(log.resource_type == "user" for log in logs)

    def test_get_audit_logs_pagination(self, db_session, test_user, test_tenant):
        """Test getting audit logs with pagination."""
        repo = AuditRepository(db_session)

        # Create multiple logs
        for i in range(5):
            repo.create_audit_log(
                user_id=test_user.id,
                tenant_id=test_tenant.id,
                action=f"action_{i}",
            )

        # Get first page
        logs_page1, total = repo.get_audit_logs(
            tenant_id=test_tenant.id, skip=0, limit=2
        )

        assert total >= 5
        assert len(logs_page1) == 2

        # Get second page
        logs_page2, total = repo.get_audit_logs(
            tenant_id=test_tenant.id, skip=2, limit=2
        )

        assert len(logs_page2) == 2
        # Verify no overlap
        page1_ids = {log.id for log in logs_page1}
        page2_ids = {log.id for log in logs_page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_get_audit_logs_by_user(self, db_session, test_user, test_tenant):
        """Test getting audit logs filtered by user."""
        repo = AuditRepository(db_session)
        from app.models.user import User
        from app.core.auth.password import hash_password

        # Create another user
        other_user = User(
            email=f"other-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password"),
            tenant_id=test_tenant.id,
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Create logs for both users
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="action1",
        )
        repo.create_audit_log(
            user_id=other_user.id,
            tenant_id=test_tenant.id,
            action="action2",
        )

        # Get logs for test_user
        logs, total = repo.get_audit_logs_by_user(
            user_id=test_user.id, tenant_id=test_tenant.id
        )

        assert total >= 1
        assert all(log.user_id == test_user.id for log in logs)

    def test_get_audit_logs_by_action(self, db_session, test_user, test_tenant):
        """Test getting audit logs filtered by action."""
        repo = AuditRepository(db_session)

        # Create logs with different actions
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="grant_permission",
        )
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="revoke_permission",
        )

        # Get logs for specific action
        logs, total = repo.get_audit_logs_by_action(
            action="grant_permission", tenant_id=test_tenant.id
        )

        assert total >= 1
        assert all(log.action == "grant_permission" for log in logs)

    def test_get_audit_logs_date_range(self, db_session, test_user, test_tenant):
        """Test getting audit logs filtered by date range."""
        repo = AuditRepository(db_session)

        # Create logs at different times
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # This log is in the past (should be excluded)
        old_log = repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="old_action",
        )
        # Update created_at to yesterday
        old_log.created_at = yesterday
        db_session.commit()

        # Create recent log
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="recent_action",
        )

        # Get logs from today onwards
        logs, total = repo.get_audit_logs(
            tenant_id=test_tenant.id,
            date_from=now - timedelta(hours=1),
            date_to=tomorrow,
        )

        assert total >= 1
        assert all(log.action == "recent_action" for log in logs if log.action)

    def test_get_audit_logs_tenant_isolation(self, db_session, test_user, test_tenant):
        """Test that audit logs are isolated by tenant."""
        repo = AuditRepository(db_session)
        from app.models.tenant import Tenant

        # Create another tenant
        other_tenant = Tenant(
            name="Other Tenant", slug=f"other-{uuid4().hex[:8]}"
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        # Create logs for both tenants
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=test_tenant.id,
            action="action1",
        )
        repo.create_audit_log(
            user_id=test_user.id,
            tenant_id=other_tenant.id,
            action="action2",
        )

        # Get logs for test_tenant
        logs, total = repo.get_audit_logs(tenant_id=test_tenant.id)

        assert all(log.tenant_id == test_tenant.id for log in logs)
        assert all(log.action != "action2" for log in logs)













