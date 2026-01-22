"""Calendar events seeder for development environment.

Creates sample calendar events and tasks with calendar integration
for testing the unified calendar view.

This seeder is idempotent - it will not create duplicate events.
"""

from datetime import datetime, timedelta

from app.models.calendar import CalendarEvent
from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.task import Task
from app.models.task_status import TaskStatus
from app.models.tenant import Tenant
from app.models.user import User


class CalendarEventsSeeder(Seeder):
    """Seeder for calendar events and tasks with calendar integration.

    Creates:
    - Calendar events (meetings, appointments)
    - Tasks with calendar dates (start_date, due_date)
    - Mix of past, current, and future events

    This seeder is idempotent - it will not create duplicate events.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get default tenant and users
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            return

        owner = db.query(User).filter(User.email == "owner@aiutox.com").first()
        admin = db.query(User).filter(User.email == "admin@aiutox.com").first()

        if not owner or not admin:
            return

        # Get task statuses
        status_open = (
            db.query(TaskStatus)
            .filter(
                TaskStatus.tenant_id == tenant.id,
                TaskStatus.name == "Por Iniciar",
            )
            .first()
        )

        status_in_progress = (
            db.query(TaskStatus)
            .filter(
                TaskStatus.tenant_id == tenant.id,
                TaskStatus.name == "En Proceso",
            )
            .first()
        )

        # Current date reference
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Calendar events
        calendar_events = [
            {
                "title": "Reunión de Planificación Mensual",
                "description": "Revisión de objetivos y planificación del próximo mes",
                "start_time": today + timedelta(days=2, hours=10),
                "end_time": today + timedelta(days=2, hours=12),
                "event_type": "meeting",
                "location": "Sala de Conferencias A",
            },
            {
                "title": "Presentación a Cliente Nuevo",
                "description": "Demo del producto para prospecto importante",
                "start_time": today + timedelta(days=5, hours=15),
                "end_time": today + timedelta(days=5, hours=16, minutes=30),
                "event_type": "meeting",
                "location": "Virtual - Zoom",
            },
            {
                "title": "Capacitación Equipo Ventas",
                "description": "Training sobre nuevas funcionalidades del sistema",
                "start_time": today + timedelta(days=7, hours=9),
                "end_time": today + timedelta(days=7, hours=13),
                "event_type": "training",
                "location": "Sala de Capacitación",
            },
            {
                "title": "Revisión Trimestral",
                "description": "Análisis de resultados del trimestre",
                "start_time": today + timedelta(days=14, hours=14),
                "end_time": today + timedelta(days=14, hours=17),
                "event_type": "meeting",
                "location": "Oficina Principal",
            },
        ]

        for event_data in calendar_events:
            existing = (
                db.query(CalendarEvent)
                .filter(
                    CalendarEvent.tenant_id == tenant.id,
                    CalendarEvent.title == event_data["title"],
                    CalendarEvent.start_time == event_data["start_time"],
                )
                .first()
            )

            if not existing:
                event = CalendarEvent(
                    tenant_id=tenant.id,
                    title=event_data["title"],
                    description=event_data["description"],
                    start_time=event_data["start_time"],
                    end_time=event_data["end_time"],
                    event_type=event_data["event_type"],
                    location=event_data.get("location"),
                    created_by_id=owner.id,
                )
                db.add(event)

        # Tasks with calendar integration
        tasks_with_dates = [
            {
                "title": "Preparar Propuesta Comercial",
                "description": "Elaborar propuesta para cliente ABC Corp",
                "status_id": status_in_progress.id if status_in_progress else None,
                "priority": "high",
                "start_date": today + timedelta(days=1),
                "due_date": today + timedelta(days=4),
                "assigned_to_id": admin.id,
            },
            {
                "title": "Actualizar Documentación Técnica",
                "description": "Revisar y actualizar docs del módulo de inventario",
                "status_id": status_open.id if status_open else None,
                "priority": "medium",
                "start_date": today + timedelta(days=3),
                "due_date": today + timedelta(days=10),
                "assigned_to_id": owner.id,
            },
            {
                "title": "Seguimiento Proveedores",
                "description": "Contactar proveedores pendientes de respuesta",
                "status_id": status_open.id if status_open else None,
                "priority": "high",
                "start_date": today,
                "due_date": today + timedelta(days=2),
                "assigned_to_id": admin.id,
            },
            {
                "title": "Análisis de Competencia",
                "description": "Investigar nuevas soluciones en el mercado",
                "status_id": status_open.id if status_open else None,
                "priority": "low",
                "start_date": today + timedelta(days=7),
                "due_date": today + timedelta(days=21),
                "assigned_to_id": owner.id,
            },
            {
                "title": "Optimización Base de Datos",
                "description": "Revisar y optimizar queries lentos",
                "status_id": status_in_progress.id if status_in_progress else None,
                "priority": "medium",
                "start_date": today - timedelta(days=2),
                "due_date": today + timedelta(days=5),
                "assigned_to_id": owner.id,
            },
        ]

        for task_data in tasks_with_dates:
            existing = (
                db.query(Task)
                .filter(
                    Task.tenant_id == tenant.id,
                    Task.title == task_data["title"],
                )
                .first()
            )

            if not existing:
                task = Task(
                    tenant_id=tenant.id,
                    title=task_data["title"],
                    description=task_data["description"],
                    status_id=task_data["status_id"],
                    priority=task_data["priority"],
                    start_date=task_data["start_date"],
                    due_date=task_data["due_date"],
                    assigned_to_id=task_data["assigned_to_id"],
                    created_by_id=owner.id,
                )
                db.add(task)

        db.commit()
