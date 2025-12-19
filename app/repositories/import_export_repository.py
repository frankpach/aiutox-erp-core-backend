"""Import/Export repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.import_export import ExportJob, ImportJob, ImportTemplate


class ImportExportRepository:
    """Repository for import/export data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Import Job methods
    def create_import_job(self, job_data: dict) -> ImportJob:
        """Create a new import job."""
        job = ImportJob(**job_data)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_import_job_by_id(self, job_id: UUID, tenant_id: UUID) -> ImportJob | None:
        """Get import job by ID and tenant."""
        return (
            self.db.query(ImportJob)
            .filter(ImportJob.id == job_id, ImportJob.tenant_id == tenant_id)
            .first()
        )

    def get_import_jobs(
        self,
        tenant_id: UUID,
        module: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ImportJob]:
        """Get import jobs with optional filters."""
        query = self.db.query(ImportJob).filter(ImportJob.tenant_id == tenant_id)

        if module:
            query = query.filter(ImportJob.module == module)
        if status:
            query = query.filter(ImportJob.status == status)

        return query.order_by(ImportJob.created_at.desc()).offset(skip).limit(limit).all()

    def update_import_job(self, job: ImportJob, job_data: dict) -> ImportJob:
        """Update import job."""
        for key, value in job_data.items():
            setattr(job, key, value)
        self.db.commit()
        self.db.refresh(job)
        return job

    def delete_import_job(self, job: ImportJob) -> None:
        """Delete import job."""
        self.db.delete(job)
        self.db.commit()

    # Import Template methods
    def create_import_template(self, template_data: dict) -> ImportTemplate:
        """Create a new import template."""
        template = ImportTemplate(**template_data)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_import_template_by_id(
        self, template_id: UUID, tenant_id: UUID
    ) -> ImportTemplate | None:
        """Get import template by ID and tenant."""
        return (
            self.db.query(ImportTemplate)
            .filter(
                ImportTemplate.id == template_id, ImportTemplate.tenant_id == tenant_id
            )
            .first()
        )

    def get_import_templates(
        self,
        tenant_id: UUID,
        module: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ImportTemplate]:
        """Get import templates with optional filters."""
        query = self.db.query(ImportTemplate).filter(ImportTemplate.tenant_id == tenant_id)

        if module:
            query = query.filter(ImportTemplate.module == module)

        return query.order_by(ImportTemplate.created_at.desc()).offset(skip).limit(limit).all()

    def update_import_template(
        self, template: ImportTemplate, template_data: dict
    ) -> ImportTemplate:
        """Update import template."""
        for key, value in template_data.items():
            setattr(template, key, value)
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_import_template(self, template: ImportTemplate) -> None:
        """Delete import template."""
        self.db.delete(template)
        self.db.commit()

    # Export Job methods
    def create_export_job(self, job_data: dict) -> ExportJob:
        """Create a new export job."""
        job = ExportJob(**job_data)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_export_job_by_id(self, job_id: UUID, tenant_id: UUID) -> ExportJob | None:
        """Get export job by ID and tenant."""
        return (
            self.db.query(ExportJob)
            .filter(ExportJob.id == job_id, ExportJob.tenant_id == tenant_id)
            .first()
        )

    def get_export_jobs(
        self,
        tenant_id: UUID,
        module: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ExportJob]:
        """Get export jobs with optional filters."""
        query = self.db.query(ExportJob).filter(ExportJob.tenant_id == tenant_id)

        if module:
            query = query.filter(ExportJob.module == module)
        if status:
            query = query.filter(ExportJob.status == status)

        return query.order_by(ExportJob.created_at.desc()).offset(skip).limit(limit).all()

    def update_export_job(self, job: ExportJob, job_data: dict) -> ExportJob:
        """Update export job."""
        for key, value in job_data.items():
            setattr(job, key, value)
        self.db.commit()
        self.db.refresh(job)
        return job

    def delete_export_job(self, job: ExportJob) -> None:
        """Delete export job."""
        self.db.delete(job)
        self.db.commit()








