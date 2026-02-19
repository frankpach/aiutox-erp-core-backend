"""Template service for document and notification template management."""

import io
import logging
from typing import Any
from uuid import UUID

from jinja2 import Environment, TemplateError
from sqlalchemy.orm import Session

from app.core.files.service import FileService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.template import Template, TemplateCategory, TemplateVersion
from app.repositories.template_repository import TemplateRepository

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """Service for rendering templates with variables."""

    def __init__(self):
        """Initialize template renderer."""
        self.jinja_env = Environment(autoescape=True)

    def render(
        self, template_content: str, variables: dict[str, Any], format: str = "html"
    ) -> str:
        """Render a template with variables.

        Args:
            template_content: Template content (Jinja2 syntax)
            variables: Variables to render template with
            format: Output format (html, text, etc.)

        Returns:
            Rendered template content

        Raises:
            ValueError: If template rendering fails
        """
        try:
            template = self.jinja_env.from_string(template_content)
            rendered = template.render(**variables)
            return rendered
        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise ValueError(f"Failed to render template: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error rendering template: {e}")
            raise ValueError(f"Failed to render template: {e}") from e

    def render_pdf(
        self, template_content: str, variables: dict[str, Any]
    ) -> bytes:
        """Render a template to PDF format.

        Args:
            template_content: Template content
            variables: Variables to render template with

        Returns:
            PDF content as bytes

        Raises:
            ValueError: If PDF rendering fails
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate

            # First render HTML content
            html_content = self.render(template_content, variables, format="html")

            # Convert HTML to PDF (simplified - in production use weasyprint or similar)
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Simple conversion (in production, use proper HTML to PDF converter)
            import re
            from html import unescape

            # Remove HTML tags and create paragraphs
            text_content = re.sub(r"<[^>]+>", "", html_content)
            elements.append(Paragraph(unescape(text_content), styles["Normal"]))

            doc.build(elements)
            return buffer.getvalue()

        except ImportError:
            logger.error("reportlab not installed, cannot render PDF")
            raise ValueError("PDF rendering requires reportlab package")
        except Exception as e:
            logger.error(f"Failed to render PDF: {e}")
            raise ValueError(f"Failed to render PDF: {e}") from e


class TemplateService:
    """Service for managing templates."""

    def __init__(
        self,
        db: Session,
        file_service: FileService | None = None,
        event_publisher: EventPublisher | None = None,
    ):
        """Initialize template service.

        Args:
            db: Database session
            file_service: FileService instance (for storing rendered templates)
            event_publisher: EventPublisher instance
        """
        self.db = db
        self.repository = TemplateRepository(db)
        self.renderer = TemplateRenderer()
        self.file_service = file_service or FileService(db)
        self.event_publisher = event_publisher or get_event_publisher()

    def create_template(
        self,
        template_data: dict,
        tenant_id: UUID,
        user_id: UUID,
    ) -> Template:
        """Create a new template."""
        template_data["tenant_id"] = tenant_id
        template_data["created_by"] = user_id

        template = self.repository.create_template(template_data)

        # Create initial version
        self.repository.create_template_version(
            {
                "tenant_id": tenant_id,
                "template_id": template.id,
                "version_number": 1,
                "content": template.content,
                "variables": template.variables,
                "is_current": True,
                "created_by": user_id,
            }
        )

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
                        event_type="template.created",
                        entity_type="template",
                        entity_id=template.id,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        metadata=EventMetadata(
                            source="template_service",
                            version="1.0",
                            additional_data={
                                "template_name": template.name,
                                "template_type": template.template_type,
                            },
                        ),
                    )

        return template

    def get_template(self, template_id: UUID, tenant_id: UUID) -> Template | None:
        """Get template by ID."""
        return self.repository.get_template_by_id(template_id, tenant_id)

    def get_templates(
        self,
        tenant_id: UUID,
        template_type: str | None = None,
        category: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Template]:
        """Get templates."""
        return self.repository.get_templates(
            tenant_id, template_type, category, is_active, skip, limit
        )

    def update_template(
        self, template_id: UUID, tenant_id: UUID, template_data: dict
    ) -> Template | None:
        """Update template and create new version if content changed."""
        template = self.repository.get_template_by_id(template_id, tenant_id)
        if not template:
            return None

        # Check if content changed
        content_changed = "content" in template_data and template_data["content"] != template.content

        # Update template
        updated_template = self.repository.update_template(template, template_data)

        # Create new version if content changed
        if content_changed:
            # Get current version number
            current_version = self.repository.get_current_version(template_id, tenant_id)
            next_version = (
                current_version.version_number + 1 if current_version else 1
            )

            # Mark old version as not current
            if current_version:
                self.repository.update_template_version(
                    current_version, {"is_current": False}
                )

            # Create new version
            self.repository.create_template_version(
                {
                    "tenant_id": tenant_id,
                    "template_id": template_id,
                    "version_number": next_version,
                    "content": updated_template.content,
                    "variables": updated_template.variables,
                    "is_current": True,
                    "created_by": template_data.get("updated_by"),
                }
            )

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
                        event_type="template.updated",
                        entity_type="template",
                        entity_id=updated_template.id,
                        tenant_id=tenant_id,
                        user_id=template.created_by,
                        metadata=EventMetadata(
                            source="template_service",
                            version="1.0",
                            additional_data={"template_name": updated_template.name},
                        ),
                    )

        return updated_template

    def delete_template(self, template_id: UUID, tenant_id: UUID) -> bool:
        """Delete template (only if not system template)."""
        template = self.repository.get_template_by_id(template_id, tenant_id)
        if not template:
            return False

        if template.is_system:
            raise ValueError("Cannot delete system template")

        self.repository.delete_template(template)
        return True

    def render_template(
        self,
        template_id: UUID,
        tenant_id: UUID,
        variables: dict[str, Any],
        format: str | None = None,
    ) -> dict[str, Any]:
        """Render a template with variables.

        Args:
            template_id: Template ID
            tenant_id: Tenant ID
            variables: Variables to render template with
            format: Output format (optional, uses template format if not provided)

        Returns:
            Dictionary with rendered_content, format, and variables_used
        """
        template = self.repository.get_template_by_id(template_id, tenant_id)
        if not template:
            raise ValueError("Template not found")

        current_version = self.repository.get_current_version(template_id, tenant_id)
        if not current_version:
            raise ValueError("Template has no current version")

        output_format = format or template.template_format

        # Render based on format
        if output_format == "pdf":
            rendered_content = self.renderer.render_pdf(
                current_version.content, variables
            )
            # For PDF, return bytes (would need to be handled differently in API)
            # For now, return as base64 string
            import base64

            rendered_content = base64.b64encode(rendered_content).decode("utf-8")
        else:
            rendered_content = self.renderer.render(
                current_version.content, variables, format=output_format
            )

        # Publish event
        from app.core.pubsub.event_helpers import safe_publish_event

        safe_publish_event(
            event_publisher=self.event_publisher,
                        event_type="template.rendered",
                        entity_type="template",
                        entity_id=template.id,
                        tenant_id=tenant_id,
            user_id=None,
                        metadata=EventMetadata(
                            source="template_service",
                            version="1.0",
                            additional_data={
                                "template_name": template.name,
                                "format": output_format,
                            },
                        ),
                    )

        return {
            "rendered_content": rendered_content,
            "format": output_format,
            "variables_used": variables,
        }

    def get_template_versions(
        self, template_id: UUID, tenant_id: UUID
    ) -> list[TemplateVersion]:
        """Get template versions."""
        return self.repository.get_template_versions(template_id, tenant_id)

    # Template Category methods
    def create_template_category(
        self, category_data: dict, tenant_id: UUID
    ) -> TemplateCategory:
        """Create a new template category."""
        category_data["tenant_id"] = tenant_id
        return self.repository.create_template_category(category_data)

    def get_template_category(
        self, category_id: UUID, tenant_id: UUID
    ) -> TemplateCategory | None:
        """Get template category by ID."""
        return self.repository.get_template_category_by_id(category_id, tenant_id)

    def get_template_categories(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[TemplateCategory]:
        """Get template categories."""
        return self.repository.get_template_categories(tenant_id, skip, limit)

    def update_template_category(
        self, category_id: UUID, tenant_id: UUID, category_data: dict
    ) -> TemplateCategory | None:
        """Update template category."""
        category = self.repository.get_template_category_by_id(category_id, tenant_id)
        if not category:
            return None

        return self.repository.update_template_category(category, category_data)

    def delete_template_category(self, category_id: UUID, tenant_id: UUID) -> bool:
        """Delete template category."""
        category = self.repository.get_template_category_by_id(category_id, tenant_id)
        if not category:
            return False

        self.repository.delete_template_category(category)
        return True

