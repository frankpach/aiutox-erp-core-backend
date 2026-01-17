"""Task templates system for QuickAdd functionality."""

from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskTemplate:
    """Task template for quick task creation."""

    def __init__(
        self,
        id: UUID,
        title: str,
        description: str,
        priority: str = "medium",
        estimated_duration: int = 30,  # minutes
        checklist_items: list[str] | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        created_by_id: UUID | None = None,
        tenant_id: UUID | None = None,
        is_public: bool = False,
        usage_count: int = 0,
        created_at: datetime | None = None,
    ):
        """Initialize task template."""
        self.id = id
        self.title = title
        self.description = description
        self.priority = priority
        self.estimated_duration = estimated_duration
        self.checklist_items = checklist_items or []
        self.tags = tags or []
        self.category = category
        self.created_by_id = created_by_id
        self.tenant_id = tenant_id
        self.is_public = is_public
        self.usage_count = usage_count
        self.created_at = created_at or datetime.utcnow()

    def to_task_data(self, **overrides) -> dict:
        """Convert template to task creation data."""
        base_data = {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "estimated_duration": self.estimated_duration,
            "tags": self.tags,
            "category": self.category,
        }

        # Apply overrides
        base_data.update(overrides)

        return base_data

    def to_dict(self) -> dict:
        """Convert template to dictionary."""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "estimated_duration": self.estimated_duration,
            "checklist_items": self.checklist_items,
            "tags": self.tags,
            "category": self.category,
            "created_by_id": str(self.created_by_id) if self.created_by_id else None,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "is_public": self.is_public,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
        }


class TaskTemplateService:
    """Service for managing task templates."""

    def __init__(self, db):
        """Initialize template service."""
        self.db = db
        self._default_templates = self._create_default_templates()

    def _create_default_templates(self) -> dict[str, TaskTemplate]:
        """Create default system templates."""
        templates = {}

        # Meeting template
        templates["meeting"] = TaskTemplate(
            id=UUID("12345678-1234-5678-9abc-123456789001"),
            title="Reunión",
            description="Plantilla para crear reuniones con checklist estándar",
            priority="high",
            estimated_duration=60,
            checklist_items=[
                "Preparar agenda",
                "Enviar convocatoria",
                "Realizar reunión",
                "Enviar acta",
                "Seguimiento de acciones"
            ],
            tags=["reunión", "meeting", "importante"],
            category="meetings",
            is_public=True,
        )

        # Bug fix template
        templates["bug_fix"] = TaskTemplate(
            id=UUID("12345678-1234-5678-9abc-123456789002"),
            title="Corrección de Bug",
            description="Plantilla para corrección de bugs técnicos",
            priority="high",
            estimated_duration=120,
            checklist_items=[
                "Reproducir el error",
                "Analizar el código",
                "Implementar solución",
                "Probar localmente",
                "Desplegar a staging",
                "Validar en producción"
            ],
            tags=["bug", "técnico", "desarrollo"],
            category="development",
            is_public=True,
        )

        # Review template
        templates["review"] = TaskTemplate(
            id=UUID("12345678-1234-5678-9abc-123456789003"),
            title="Revisión de Documento",
            description="Plantilla para revisión de documentos o código",
            priority="medium",
            estimated_duration=45,
            checklist_items=[
                "Leer documento completo",
                "Verificar estructura",
                "Revisar contenido",
                "Comentar mejoras",
                "Aprobar o solicitar cambios"
            ],
            tags=["revisión", "documento", "código"],
            category="reviews",
            is_public=True,
        )

        # Research template
        templates["research"] = TaskTemplate(
            id=UUID("12345678-1234-5678-9abc-123456789004"),
            title="Investigación",
            description="Plantilla para tareas de investigación",
            priority="medium",
            estimated_duration=180,
            checklist_items=[
                "Definir objetivos",
                "Recopilar información",
                "Analizar fuentes",
                "Sintetizar hallazgos",
                "Preparar informe",
                "Presentar resultados"
            ],
            tags=["investigación", "análisis", "estudio"],
            category="research",
            is_public=True,
        )

        # Customer support template
        templates["support"] = TaskTemplate(
            id=UUID("12345678-1234-5678-9abc-123456789005"),
            title="Soporte al Cliente",
            description="Plantilla para tickets de soporte",
            priority="high",
            estimated_duration=30,
            checklist_items=[
                "Recibir ticket",
                "Analizar problema",
                "Contactar cliente",
                "Proponer solución",
                "Implementar solución",
                "Verificar satisfacción"
            ],
            tags=["soporte", "cliente", "helpdesk"],
            category="support",
            is_public=True,
        )

        return templates

    def get_template(self, template_id: str) -> TaskTemplate | None:
        """Get template by ID."""
        # Check default templates
        if template_id in self._default_templates:
            return self._default_templates[template_id]

        # TODO: Check user templates from database
        # For now, return None
        return None

    def get_templates(
        self,
        tenant_id: UUID,
        user_id: UUID | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        include_public: bool = True
    ) -> list[TaskTemplate]:
        """Get available templates."""
        templates = []

        # Add default templates
        for template in self._default_templates.values():
            if include_public and template.is_public:
                templates.append(template)

        # TODO: Add user templates from database

        # Filter by category
        if category:
            templates = [t for t in templates if t.category == category]

        # Filter by tags
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]

        # Sort by usage count (most used first)
        templates.sort(key=lambda t: t.usage_count, reverse=True)

        return templates

    def get_template_categories(self, tenant_id: UUID) -> list[str]:
        """Get available template categories."""
        categories = set()

        # Add categories from default templates
        for template in self._default_templates.values():
            if template.is_public:
                categories.add(template.category)

        # TODO: Add categories from user templates

        return sorted(list(categories))

    def create_task_from_template(
        self,
        template_id: str,
        tenant_id: UUID,
        created_by_id: UUID,
        overrides: dict | None = None
    ) -> dict:
        """Create task data from template."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Increment usage count
        template.usage_count += 1

        # Get task data from template
        task_data = template.to_task_data(
            tenant_id=str(tenant_id),
            created_by_id=str(created_by_id),
            **(overrides or {})
        )

        # Add checklist items if they exist
        if template.checklist_items:
            task_data["checklist_items"] = [
                {"title": item, "completed": False}
                for item in template.checklist_items
            ]

        logger.info(f"Task created from template {template_id}")

        return task_data

    def create_template(
        self,
        title: str,
        description: str,
        tenant_id: UUID,
        created_by_id: UUID,
        priority: str = "medium",
        estimated_duration: int = 30,
        checklist_items: list[str] | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        is_public: bool = False
    ) -> TaskTemplate:
        """Create a new template."""
        template = TaskTemplate(
            id=UUID(),
            title=title,
            description=description,
            priority=priority,
            estimated_duration=estimated_duration,
            checklist_items=checklist_items,
            tags=tags,
            category=category,
            created_by_id=created_by_id,
            tenant_id=tenant_id,
            is_public=is_public,
        )

        # TODO: Save to database
        logger.info(f"Template created: {title}")

        return template

    def update_template(
        self,
        template_id: UUID,
        updates: dict
    ) -> TaskTemplate | None:
        """Update an existing template."""
        # TODO: Update in database
        logger.info(f"Template updated: {template_id}")
        return None

    def delete_template(self, template_id: UUID, tenant_id: UUID) -> bool:
        """Delete a template."""
        # TODO: Delete from database
        logger.info(f"Template deleted: {template_id}")
        return True

    def get_popular_templates(
        self,
        tenant_id: UUID,
        limit: int = 10
    ) -> list[TaskTemplate]:
        """Get most used templates."""
        templates = self.get_templates(tenant_id, include_public=True)
        return templates[:limit]


# Global template service instance
task_template_service = None

def get_task_template_service(db) -> TaskTemplateService:
    """Get task template service instance."""
    global task_template_service
    if task_template_service is None:
        task_template_service = TaskTemplateService(db)
    return task_template_service
