"""Unit tests for AuditService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService


class TestAuditService:
    """Test suite for AuditService."""

    def test_get_audit_logs_with_filters(self, db_session, test_tenant):
        """Test getting audit logs with filters."""
        service = AuditService(db_session)

        # Mock audit logs
        from app.models.audit_log import AuditLog

        mock_logs = []
        for i in range(3):
            log = AuditLog(
                id=uuid4(),
                tenant_id=test_tenant.id,
                action=f"action_{i}",
                resource_type="user",
                created_at=datetime.now(timezone.utc),
            )
            mock_logs.append(log)

        service.repository.get_audit_logs = Mock(return_value=(mock_logs, 3))

        logs, total = service.get_audit_logs(
            tenant_id=test_tenant.id,
            user_id=uuid4(),
            action="action_1",
        )

        assert len(logs) == 3
        assert total == 3
        # Service converts to AuditLogResponse schemas
        from app.schemas.audit import AuditLogResponse
        assert all(isinstance(log, AuditLogResponse) for log in logs)
        service.repository.get_audit_logs.assert_called_once()

    def test_get_audit_logs_pagination(self, db_session, test_tenant):
        """Test getting audit logs with pagination."""
        service = AuditService(db_session)

        from app.models.audit_log import AuditLog

        mock_logs = []
        for i in range(2):
            log = AuditLog(
                id=uuid4(),
                tenant_id=test_tenant.id,
                action=f"action_{i}",
                created_at=datetime.now(timezone.utc),
            )
            mock_logs.append(log)

        service.repository.get_audit_logs = Mock(return_value=(mock_logs, 10))

        logs, total = service.get_audit_logs(
            tenant_id=test_tenant.id, skip=0, limit=2
        )

        assert len(logs) == 2
        assert total == 10
        service.repository.get_audit_logs.assert_called_once_with(
            tenant_id=test_tenant.id,
            user_id=None,
            action=None,
            resource_type=None,
            date_from=None,
            date_to=None,
            ip_address=None,
            user_agent=None,
            details_search=None,
            skip=0,
            limit=2,
        )

    def test_get_audit_logs_by_user(self, db_session, test_user, test_tenant):
        """Test getting audit logs filtered by user."""
        service = AuditService(db_session)

        from app.models.audit_log import AuditLog

        mock_logs = [
            AuditLog(
                id=uuid4(),
                user_id=test_user.id,
                tenant_id=test_tenant.id,
                action="create_user",
                created_at=datetime.now(timezone.utc),
            )
        ]

        service.repository.get_audit_logs = Mock(return_value=(mock_logs, 1))

        logs, total = service.get_audit_logs(
            tenant_id=test_tenant.id, user_id=test_user.id
        )

        assert len(logs) == 1
        assert total == 1
        service.repository.get_audit_logs.assert_called_once_with(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            action=None,
            resource_type=None,
            date_from=None,
            date_to=None,
            skip=0,
            limit=100,
        )

    def test_get_audit_logs_by_action(self, db_session, test_tenant):
        """Test getting audit logs filtered by action."""
        service = AuditService(db_session)

        from app.models.audit_log import AuditLog

        mock_logs = [
            AuditLog(
                id=uuid4(),
                tenant_id=test_tenant.id,
                action="grant_permission",
                created_at=datetime.now(timezone.utc),
            )
        ]

        service.repository.get_audit_logs = Mock(return_value=(mock_logs, 1))

        logs, total = service.get_audit_logs(
            tenant_id=test_tenant.id, action="grant_permission"
        )

        assert len(logs) == 1
        assert total == 1
        service.repository.get_audit_logs.assert_called_once_with(
            tenant_id=test_tenant.id,
            user_id=None,
            action="grant_permission",
            resource_type=None,
            date_from=None,
            date_to=None,
            skip=0,
            limit=100,
        )

    def test_get_audit_logs_date_range(self, db_session, test_tenant):
        """Test getting audit logs filtered by date range."""
        service = AuditService(db_session)

        from app.models.audit_log import AuditLog

        date_from = datetime.now(timezone.utc) - timedelta(days=1)
        date_to = datetime.now(timezone.utc)

        mock_logs = [
            AuditLog(
                id=uuid4(),
                tenant_id=test_tenant.id,
                action="action",
                created_at=datetime.now(timezone.utc),
            )
        ]

        service.repository.get_audit_logs = Mock(return_value=(mock_logs, 1))

        logs, total = service.get_audit_logs(
            tenant_id=test_tenant.id, date_from=date_from, date_to=date_to
        )

        assert len(logs) == 1
        assert total == 1
        service.repository.get_audit_logs.assert_called_once_with(
            tenant_id=test_tenant.id,
            user_id=None,
            action=None,
            resource_type=None,
            date_from=date_from,
            date_to=date_to,
            skip=0,
            limit=100,
        )

