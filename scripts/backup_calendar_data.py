"""
Script de backup para datos de calendario y tareas.

Crea un backup completo de:
- task_statuses
- task_templates
- tasks (con campos extendidos)
- calendar_events

El backup se guarda en formato JSON con timestamp.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.models.calendar_event import CalendarEvent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.task import Task
from app.models.task_status import TaskStatus
from app.models.task_template import TaskTemplate


def serialize_model(obj):
    """Serializa un modelo SQLAlchemy a diccionario."""
    if obj is None:
        return None

    data = {}
    for column in obj.__table__.columns:
        value = getattr(obj, column.name)
        if value is not None:
            # Convertir tipos especiales a string
            if hasattr(value, 'isoformat'):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = str(value)
        else:
            data[column.name] = None
    return data


def backup_calendar_data(tenant_id: str | None = None, output_dir: str = "backups"):
    """
    Crea backup de datos de calendario y tareas.

    Args:
        tenant_id: ID del tenant (opcional, si no se especifica hace backup de todos)
        output_dir: Directorio donde guardar el backup
    """
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    try:
        # Crear directorio de backups si no existe
        backup_path = Path(output_dir)
        backup_path.mkdir(exist_ok=True)

        # Timestamp para el nombre del archivo
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        tenant_suffix = f"_tenant_{tenant_id}" if tenant_id else "_all"
        filename = f"calendar_backup_{timestamp}{tenant_suffix}.json"
        filepath = backup_path / filename

        backup_data = {
            "timestamp": timestamp,
            "tenant_id": tenant_id,
            "task_statuses": [],
            "task_templates": [],
            "tasks": [],
            "calendar_events": [],
        }

        # Backup task_statuses
        query = db.query(TaskStatus)
        if tenant_id:
            query = query.filter(TaskStatus.tenant_id == tenant_id)

        for status in query.all():
            backup_data["task_statuses"].append(serialize_model(status))

        # Backup task_templates
        query = db.query(TaskTemplate)
        if tenant_id:
            query = query.filter(TaskTemplate.tenant_id == tenant_id)

        for template in query.all():
            backup_data["task_templates"].append(serialize_model(template))

        # Backup tasks
        query = db.query(Task)
        if tenant_id:
            query = query.filter(Task.tenant_id == tenant_id)

        for task in query.all():
            backup_data["tasks"].append(serialize_model(task))

        # Backup calendar_events
        query = db.query(CalendarEvent)
        if tenant_id:
            query = query.filter(CalendarEvent.tenant_id == tenant_id)

        for event in query.all():
            backup_data["calendar_events"].append(serialize_model(event))

        # Guardar backup
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Backup creado exitosamente: {filepath}")
        print(f"   - Task Statuses: {len(backup_data['task_statuses'])}")
        print(f"   - Task Templates: {len(backup_data['task_templates'])}")
        print(f"   - Tasks: {len(backup_data['tasks'])}")
        print(f"   - Calendar Events: {len(backup_data['calendar_events'])}")

        return str(filepath)

    finally:
        db.close()


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Backup de datos de calendario y tareas"
    )
    parser.add_argument(
        "--tenant-id",
        type=str,
        help="ID del tenant (opcional, si no se especifica hace backup de todos)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backups",
        help="Directorio donde guardar el backup (default: backups)",
    )

    args = parser.parse_args()
    backup_calendar_data(tenant_id=args.tenant_id, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
