"""Task templates seeder for development environment.

Creates example task templates with predefined checklists and configurations
for common business processes.

This seeder is idempotent - it will not create duplicate templates.
"""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.task_status import TaskStatus
from app.models.task_template import TaskTemplate
from app.models.tenant import Tenant
from app.models.user import User


class TaskTemplatesSeeder(Seeder):
    """Seeder for task templates with example business processes.

    Creates templates for:
    - Gestión de Llamada a Proveedores
    - Proceso de Onboarding Cliente
    - Revisión de Inventario Mensual
    - Seguimiento de Venta

    This seeder is idempotent - it will not create duplicate templates.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get default tenant and owner user
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            return

        owner = db.query(User).filter(User.email == "owner@aiutox.com").first()
        if not owner:
            return

        # Get default status "Por Iniciar"
        default_status = (
            db.query(TaskStatus)
            .filter(
                TaskStatus.tenant_id == tenant.id,
                TaskStatus.name == "Por Iniciar",
            )
            .first()
        )

        # Template definitions
        templates = [
            {
                "name": "Gestión de Llamada a Proveedores",
                "description": "Proceso estándar para gestionar llamadas y seguimiento con proveedores",
                "estimated_hours": 2,
                "checklist_items": [
                    {"text": "Preparar lista de puntos a tratar", "order": 1, "completed": False},
                    {"text": "Realizar llamada telefónica", "order": 2, "completed": False},
                    {"text": "Documentar acuerdos y compromisos", "order": 3, "completed": False},
                    {"text": "Enviar email de confirmación", "order": 4, "completed": False},
                    {"text": "Programar seguimiento", "order": 5, "completed": False},
                ],
            },
            {
                "name": "Proceso de Onboarding Cliente",
                "description": "Pasos para incorporar un nuevo cliente al sistema",
                "estimated_hours": 4,
                "checklist_items": [
                    {"text": "Recopilar información del cliente", "order": 1, "completed": False},
                    {"text": "Crear cuenta en el sistema", "order": 2, "completed": False},
                    {"text": "Configurar permisos y accesos", "order": 3, "completed": False},
                    {"text": "Realizar capacitación inicial", "order": 4, "completed": False},
                    {"text": "Enviar documentación de bienvenida", "order": 5, "completed": False},
                    {"text": "Programar seguimiento a 7 días", "order": 6, "completed": False},
                ],
            },
            {
                "name": "Revisión de Inventario Mensual",
                "description": "Proceso mensual de revisión y ajuste de inventario",
                "estimated_hours": 8,
                "checklist_items": [
                    {"text": "Exportar reporte de inventario actual", "order": 1, "completed": False},
                    {"text": "Realizar conteo físico", "order": 2, "completed": False},
                    {"text": "Identificar discrepancias", "order": 3, "completed": False},
                    {"text": "Ajustar cantidades en sistema", "order": 4, "completed": False},
                    {"text": "Documentar causas de diferencias", "order": 5, "completed": False},
                    {"text": "Generar reporte final", "order": 6, "completed": False},
                ],
            },
            {
                "name": "Seguimiento de Venta",
                "description": "Proceso de seguimiento post-venta para asegurar satisfacción del cliente",
                "estimated_hours": 1,
                "checklist_items": [
                    {"text": "Verificar entrega del producto/servicio", "order": 1, "completed": False},
                    {"text": "Contactar al cliente para feedback", "order": 2, "completed": False},
                    {"text": "Registrar comentarios y sugerencias", "order": 3, "completed": False},
                    {"text": "Resolver cualquier inconveniente", "order": 4, "completed": False},
                    {"text": "Solicitar testimonio o referencia", "order": 5, "completed": False},
                ],
            },
        ]

        # Create templates
        for template_data in templates:
            existing = (
                db.query(TaskTemplate)
                .filter(
                    TaskTemplate.tenant_id == tenant.id,
                    TaskTemplate.name == template_data["name"],
                )
                .first()
            )

            if not existing:
                template = TaskTemplate(
                    tenant_id=tenant.id,
                    name=template_data["name"],
                    description=template_data["description"],
                    estimated_hours=template_data["estimated_hours"],
                    default_status_id=default_status.id if default_status else None,
                    checklist_items=template_data["checklist_items"],
                    created_by_id=owner.id,
                )
                db.add(template)

        db.commit()
