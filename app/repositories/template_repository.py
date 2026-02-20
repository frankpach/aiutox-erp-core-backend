"""Template repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.template import Template, TemplateCategory, TemplateVersion


class TemplateRepository:
    """Repository for template data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Template methods
    def create_template(self, template_data: dict) -> Template:
        """Create a new template."""
        template = Template(**template_data)
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_template_by_id(self, template_id: UUID, tenant_id: UUID) -> Template | None:
        """Get template by ID and tenant."""
        return (
            self.db.query(Template)
            .filter(Template.id == template_id, Template.tenant_id == tenant_id)
            .first()
        )

    def get_templates(
        self,
        tenant_id: UUID,
        template_type: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Template]:
        """Get templates with optional filters."""
        query = self.db.query(Template).filter(Template.tenant_id == tenant_id)

        if template_type:
            query = query.filter(Template.template_type == template_type)
        if category:
            query = query.filter(Template.category == category)
        if is_active is not None:
            query = query.filter(Template.is_active == is_active)

        return (
            query.order_by(Template.created_at.desc()).offset(skip).limit(limit).all()
        )

    def update_template(self, template: Template, template_data: dict) -> Template:
        """Update template."""
        for key, value in template_data.items():
            setattr(template, key, value)
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template: Template) -> None:
        """Delete template."""
        self.db.delete(template)
        self.db.commit()

    # Template Version methods
    def create_template_version(self, version_data: dict) -> TemplateVersion:
        """Create a new template version."""
        version = TemplateVersion(**version_data)
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_template_versions(
        self, template_id: UUID, tenant_id: UUID, is_current: bool | None = None
    ) -> list[TemplateVersion]:
        """Get template versions."""
        query = self.db.query(TemplateVersion).filter(
            TemplateVersion.template_id == template_id,
            TemplateVersion.tenant_id == tenant_id,
        )

        if is_current is not None:
            query = query.filter(TemplateVersion.is_current == is_current)

        return query.order_by(TemplateVersion.version_number.desc()).all()

    def get_current_version(
        self, template_id: UUID, tenant_id: UUID
    ) -> TemplateVersion | None:
        """Get current template version."""
        return (
            self.db.query(TemplateVersion)
            .filter(
                TemplateVersion.template_id == template_id,
                TemplateVersion.tenant_id == tenant_id,
                TemplateVersion.is_current,
            )
            .first()
        )

    def update_template_version(
        self, version: TemplateVersion, version_data: dict
    ) -> TemplateVersion:
        """Update template version."""
        for key, value in version_data.items():
            setattr(version, key, value)
        self.db.commit()
        self.db.refresh(version)
        return version

    # Template Category methods
    def create_template_category(self, category_data: dict) -> TemplateCategory:
        """Create a new template category."""
        category = TemplateCategory(**category_data)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def get_template_categories(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[TemplateCategory]:
        """Get template categories."""
        return (
            self.db.query(TemplateCategory)
            .filter(TemplateCategory.tenant_id == tenant_id)
            .order_by(TemplateCategory.name.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_template_category_by_id(
        self, category_id: UUID, tenant_id: UUID
    ) -> TemplateCategory | None:
        """Get template category by ID."""
        return (
            self.db.query(TemplateCategory)
            .filter(
                TemplateCategory.id == category_id,
                TemplateCategory.tenant_id == tenant_id,
            )
            .first()
        )

    def update_template_category(
        self, category: TemplateCategory, category_data: dict
    ) -> TemplateCategory:
        """Update template category."""
        for key, value in category_data.items():
            setattr(category, key, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_template_category(self, category: TemplateCategory) -> None:
        """Delete template category."""
        self.db.delete(category)
        self.db.commit()
