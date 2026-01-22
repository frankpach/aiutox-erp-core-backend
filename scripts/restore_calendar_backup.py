"""
Script de restauración para backups de calendario y tareas.

Restaura datos desde un archivo de backup JSON creado por backup_calendar_data.py
"""

import argparse
import json
from pathlib import Path
from uuid import UUID

from app.models.calendar_event import CalendarEvent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.task import Task
from app.models.task_status import TaskStatus
from app.models.task_template import TaskTemplate


def parse_uuid(value: str | None) -> UUID | None:
    """Convierte string a UUID, retorna None si es None o inválido."""
    if value is None or value == "None":
        return None
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


def restore_calendar_backup(backup_file: str, skip_existing: bool = True):
    """
    Restaura datos desde un archivo de backup.

    Args:
        backup_file: Ruta al archivo de backup JSON
        skip_existing: Si True, omite registros que ya existen (por ID)
    """
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    try:
        # Leer archivo de backup
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Archivo de backup no encontrado: {backup_file}")

        with open(backup_path, encoding="utf-8") as f:
            backup_data = json.load(f)

        print(f"📦 Restaurando backup desde: {backup_file}")
        print(f"   Timestamp: {backup_data.get('timestamp', 'N/A')}")
        print(f"   Tenant ID: {backup_data.get('tenant_id', 'Todos')}")

        stats = {
            "task_statuses": {"restored": 0, "skipped": 0},
            "task_templates": {"restored": 0, "skipped": 0},
            "tasks": {"restored": 0, "skipped": 0},
            "calendar_events": {"restored": 0, "skipped": 0},
        }

        # Restaurar task_statuses
        print("\n🔄 Restaurando task_statuses...")
        for status_data in backup_data.get("task_statuses", []):
            status_id = parse_uuid(status_data.get("id"))

            if skip_existing and db.query(TaskStatus).filter(TaskStatus.id == status_id).first():
                stats["task_statuses"]["skipped"] += 1
                continue

            status = TaskStatus(
                id=status_id,
                tenant_id=parse_uuid(status_data["tenant_id"]),
                name=status_data["name"],
                type=status_data["type"],
                color=status_data["color"],
                is_system=status_data.get("is_system", False),
                order=int(status_data.get("order", 0)),
            )
            db.add(status)
            stats["task_statuses"]["restored"] += 1

        db.commit()

        # Restaurar task_templates
        print("🔄 Restaurando task_templates...")
        for template_data in backup_data.get("task_templates", []):
            template_id = parse_uuid(template_data.get("id"))

            if skip_existing and db.query(TaskTemplate).filter(TaskTemplate.id == template_id).first():
                stats["task_templates"]["skipped"] += 1
                continue

            # Parsear checklist_items si es string JSON
            checklist = template_data.get("checklist_items")
            if isinstance(checklist, str):
                checklist = json.loads(checklist) if checklist else None

            template = TaskTemplate(
                id=template_id,
                tenant_id=parse_uuid(template_data["tenant_id"]),
                name=template_data["name"],
                description=template_data.get("description"),
                estimated_hours=int(template_data["estimated_hours"]) if template_data.get("estimated_hours") else None,
                default_status_id=parse_uuid(template_data.get("default_status_id")),
                checklist_items=checklist,
                created_by_id=parse_uuid(template_data["created_by_id"]),
            )
            db.add(template)
            stats["task_templates"]["restored"] += 1

        db.commit()

        # Restaurar tasks (solo campos extendidos si ya existen)
        print("🔄 Actualizando tasks con campos extendidos...")
        for task_data in backup_data.get("tasks", []):
            task_id = parse_uuid(task_data.get("id"))

            existing_task = db.query(Task).filter(Task.id == task_id).first()
            if existing_task:
                # Actualizar campos extendidos
                if "status_id" in task_data:
                    existing_task.status_id = parse_uuid(task_data["status_id"])
                if "board_order" in task_data:
                    existing_task.board_order = int(task_data["board_order"]) if task_data["board_order"] else None
                if "template_id" in task_data:
                    existing_task.template_id = parse_uuid(task_data["template_id"])
                stats["tasks"]["restored"] += 1
            else:
                stats["tasks"]["skipped"] += 1

        db.commit()

        # Restaurar calendar_events
        print("🔄 Restaurando calendar_events...")
        for event_data in backup_data.get("calendar_events", []):
            event_id = parse_uuid(event_data.get("id"))

            if skip_existing and db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first():
                stats["calendar_events"]["skipped"] += 1
                continue

            event = CalendarEvent(
                id=event_id,
                tenant_id=parse_uuid(event_data["tenant_id"]),
                title=event_data["title"],
                description=event_data.get("description"),
                start_time=event_data["start_time"],
                end_time=event_data["end_time"],
                event_type=event_data.get("event_type"),
                location=event_data.get("location"),
                created_by_id=parse_uuid(event_data["created_by_id"]),
            )
            db.add(event)
            stats["calendar_events"]["restored"] += 1

        db.commit()

        # Mostrar estadísticas
        print("\n✅ Restauración completada:")
        for entity, counts in stats.items():
            print(f"   {entity}: {counts['restored']} restaurados, {counts['skipped']} omitidos")

    except Exception as e:
        print(f"❌ Error durante la restauración: {e}")
        db.rollback()
        raise

    finally:
        db.close()


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Restaurar backup de datos de calendario y tareas"
    )
    parser.add_argument(
        "backup_file",
        type=str,
        help="Ruta al archivo de backup JSON",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribir registros existentes (por defecto se omiten)",
    )

    args = parser.parse_args()
    restore_calendar_backup(
        backup_file=args.backup_file,
        skip_existing=not args.overwrite
    )


if __name__ == "__main__":
    main()
