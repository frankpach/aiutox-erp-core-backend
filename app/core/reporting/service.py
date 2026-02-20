"""Reporting service for report management."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.reporting.engine import ReportingEngine
from app.models.reporting import ReportDefinition
from app.repositories.reporting_repository import ReportingRepository

logger = logging.getLogger(__name__)


class ReportingService:
    """Service for managing reports."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = ReportingRepository(db)
        self.engine = ReportingEngine(db)

    def create_report(
        self,
        tenant_id: UUID,
        name: str,
        data_source_type: str,
        visualization_type: str,
        created_by: UUID,
        description: str | None = None,
        filters: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> ReportDefinition:
        """Create a new report definition.

        Args:
            tenant_id: Tenant ID
            name: Report name
            data_source_type: Data source type (e.g., 'products')
            visualization_type: Visualization type ('table', 'chart', 'kpi')
            created_by: User ID who created the report
            description: Report description (optional)
            filters: Filter configuration (optional)
            config: Visualization configuration (optional)

        Returns:
            Created report definition
        """
        report_data = {
            "tenant_id": tenant_id,
            "name": name,
            "description": description,
            "data_source_type": data_source_type,
            "filters": filters,
            "visualization_type": visualization_type,
            "config": config,
            "created_by": created_by,
        }
        report = self.repository.create_report(report_data)
        logger.info(f"Created report '{name}' (ID: {report.id}) for tenant {tenant_id}")
        return report

    def get_report(self, report_id: UUID, tenant_id: UUID) -> ReportDefinition | None:
        """Get a report by ID.

        Args:
            report_id: Report ID
            tenant_id: Tenant ID

        Returns:
            Report or None if not found
        """
        return self.repository.get_report_by_id(report_id, tenant_id)

    def get_all_reports(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ReportDefinition]:
        """Get all reports for a tenant.

        Args:
            tenant_id: Tenant ID
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of reports
        """
        return self.repository.get_all_reports(tenant_id, skip, limit)

    def update_report(
        self,
        report_id: UUID,
        tenant_id: UUID,
        name: str | None = None,
        description: str | None = None,
        filters: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ) -> ReportDefinition | None:
        """Update a report.

        Args:
            report_id: Report ID
            tenant_id: Tenant ID
            name: New name (optional)
            description: New description (optional)
            filters: New filters (optional)
            config: New config (optional)

        Returns:
            Updated report or None if not found
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if filters is not None:
            update_data["filters"] = filters
        if config is not None:
            update_data["config"] = config

        updated_report = self.repository.update_report(
            report_id, tenant_id, update_data
        )
        if updated_report:
            logger.info(f"Updated report {report_id} for tenant {tenant_id}")
        return updated_report

    def delete_report(self, report_id: UUID, tenant_id: UUID) -> bool:
        """Delete a report.

        Args:
            report_id: Report ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        result = self.repository.delete_report(report_id, tenant_id)
        if result:
            logger.info(f"Deleted report {report_id} for tenant {tenant_id}")
        return result

    async def execute_report(
        self,
        report_id: UUID,
        tenant_id: UUID,
        filters: dict[str, Any] | None = None,
        pagination: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Execute a report.

        Args:
            report_id: Report ID
            tenant_id: Tenant ID
            filters: Additional filters to apply
            pagination: Pagination configuration

        Returns:
            Report execution result

        Raises:
            ValueError: If report not found or data source not registered
        """
        report = self.repository.get_report_by_id(report_id, tenant_id)
        if not report:
            raise ValueError(f"Report with ID {report_id} not found")

        return await self.engine.execute(report, filters, pagination)
