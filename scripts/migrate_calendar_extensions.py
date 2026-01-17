"""
Script para ejecutar migración de extensiones de calendario
y migrar datos existentes de Tasks a CalendarEvents.

Uso:
    python scripts/migrate_calendar_extensions.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.core.db.session import get_db
from app.core.calendar.sync_service import CalendarSyncService
from app.models.task import Task


def migrate_tasks_to_events(db: Session) -> None:
    """Migrar Tasks existentes con due_date a CalendarEvents."""
    print("Iniciando migración de Tasks a CalendarEvents...")

    sync_service = CalendarSyncService(db)

    # Obtener todas las tasks con due_date
    tasks = db.query(Task).filter(Task.due_date.isnot(None)).all()

    print(f"Encontradas {len(tasks)} tasks con due_date")

    migrated = 0
    errors = 0

    for task in tasks:
        try:
            event = sync_service.sync_task_to_event(task)
            if event:
                migrated += 1
                print(f"✓ Task '{task.title}' migrada a CalendarEvent")
        except Exception as e:
            errors += 1
            print(f"✗ Error migrando task '{task.title}': {str(e)}")

    print(f"\nMigración completada:")
    print(f"  - Exitosas: {migrated}")
    print(f"  - Errores: {errors}")
    print(f"  - Total: {len(tasks)}")


def main():
    """Función principal."""
    print("=" * 60)
    print("Migración de Extensiones de Calendario")
    print("=" * 60)
    print()

    # Obtener sesión de base de datos
    db = next(get_db())

    try:
        # Ejecutar migración de datos
        migrate_tasks_to_events(db)

        print("\n✓ Migración completada exitosamente")

    except Exception as e:
        print(f"\n✗ Error durante la migración: {str(e)}")
        db.rollback()
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
