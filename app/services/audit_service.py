"""Audit service for querying audit logs."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogResponse


class AuditService:
    """Service for querying audit logs."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.repository = AuditRepository(db)

    def get_audit_logs(
        self,
        tenant_id: UUID,
        user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[AuditLogResponse], int]:
        """
        Get audit logs with filters and pagination.

        Args:
            tenant_id: Tenant ID (required for multi-tenancy).
            user_id: Filter by user ID (optional).
            action: Filter by action type (optional).
            resource_type: Filter by resource type (optional).
            date_from: Filter by start date (optional).
            date_to: Filter by end date (optional).
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (list of AuditLogResponse, total count).
        """
        logs, total = self.repository.get_audit_logs(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            date_from=date_from,
            date_to=date_to,
            skip=skip,
            limit=limit,
        )

        # Convert to response schemas
        log_responses = [AuditLogResponse.model_validate(log) for log in logs]

        return log_responses, total

