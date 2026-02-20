"""Reporting repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.reporting import ReportDefinition


class ReportingRepository:
    """Repository for reporting data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # ReportDefinition operations
    def create_report(self, report_data: dict) -> ReportDefinition:
        """Create a new report definition."""
        report = ReportDefinition(**report_data)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_report_by_id(
        self, report_id: UUID, tenant_id: UUID
    ) -> ReportDefinition | None:
        """Get report by ID and tenant ID."""
        return (
            self.db.query(ReportDefinition)
            .filter(
                ReportDefinition.id == report_id,
                ReportDefinition.tenant_id == tenant_id,
            )
            .first()
        )

    def get_all_reports(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[ReportDefinition]:
        """Get all reports by tenant with pagination."""
        return (
            self.db.query(ReportDefinition)
            .filter(ReportDefinition.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_report(
        self, report_id: UUID, tenant_id: UUID, report_data: dict
    ) -> ReportDefinition | None:
        """Update a report."""
        report = self.get_report_by_id(report_id, tenant_id)
        if not report:
            return None
        for key, value in report_data.items():
            setattr(report, key, value)
        self.db.commit()
        self.db.refresh(report)
        return report

    def delete_report(self, report_id: UUID, tenant_id: UUID) -> bool:
        """Delete a report."""
        report = self.get_report_by_id(report_id, tenant_id)
        if not report:
            return False
        self.db.delete(report)
        self.db.commit()
        return True
