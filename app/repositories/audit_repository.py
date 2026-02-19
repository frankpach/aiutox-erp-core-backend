"""Audit log repository for data access operations."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditRepository:
    """Repository for audit log data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_audit_log(
        self,
        user_id: UUID | None,
        tenant_id: UUID,
        action: str,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            user_id: User who performed the action (None for system actions).
            tenant_id: Tenant ID for multi-tenancy.
            action: Action type (e.g., 'grant_permission', 'create_user').
            resource_type: Type of resource affected (e.g., 'user', 'permission').
            resource_id: ID of the resource affected.
            details: Additional details as JSON.
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            Created AuditLog instance.
        """
        audit_log = AuditLog(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log

    def get_audit_logs(
        self,
        tenant_id: UUID,
        user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details_search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        """
        Get audit logs with filters and pagination.

        Args:
            tenant_id: Tenant ID (required for multi-tenancy).
            user_id: Filter by user ID (optional).
            action: Filter by action type (optional).
            resource_type: Filter by resource type (optional).
            date_from: Filter by start date (optional).
            date_to: Filter by end date (optional).
            ip_address: Filter by IP address (partial match, optional).
            user_agent: Filter by user agent (partial match, optional).
            details_search: Search in details JSON (partial match, optional).
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (list of AuditLog instances, total count).
        """
        from sqlalchemy import String, cast

        query = self.db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)

        # Apply filters
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if action is not None:
            query = query.filter(AuditLog.action == action)
        if resource_type is not None:
            query = query.filter(AuditLog.resource_type == resource_type)
        if date_from is not None:
            query = query.filter(AuditLog.created_at >= date_from)
        if date_to is not None:
            query = query.filter(AuditLog.created_at <= date_to)
        if ip_address is not None:
            query = query.filter(AuditLog.ip_address.ilike(f"%{ip_address}%"))
        if user_agent is not None:
            query = query.filter(AuditLog.user_agent.ilike(f"%{user_agent}%"))
        if details_search is not None:
            # Search in details JSON by casting to text and using ilike
            query = query.filter(
                cast(AuditLog.details, String).ilike(f"%{details_search}%")
            )

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

        return logs, total

    def get_audit_logs_by_user(
        self,
        user_id: UUID,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        """
        Get audit logs for a specific user.

        Args:
            user_id: User ID.
            tenant_id: Tenant ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (list of AuditLog instances, total count).
        """
        return self.get_audit_logs(
            tenant_id=tenant_id,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    def get_audit_logs_by_action(
        self,
        action: str,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLog], int]:
        """
        Get audit logs for a specific action type.

        Args:
            action: Action type.
            tenant_id: Tenant ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (list of AuditLog instances, total count).
        """
        return self.get_audit_logs(
            tenant_id=tenant_id,
            action=action,
            skip=skip,
            limit=limit,
        )

