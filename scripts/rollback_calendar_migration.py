"""
Script de rollback para la migración de task_statuses y task_templates.

Este script permite revertir los cambios de la migración add_task_statuses_templates
de forma segura, preservando los datos existentes cuando sea posible.
"""

import argparse
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings


def rollback_migration(create_backup: bool = True):
    """
    Revierte la migración de task_statuses y task_templates.

    Args:
        create_backup: Si True, crea un backup antes del rollback
    """
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    session_local = sessionmaker(bind=engine)
    db = session_local()

    try:
        print("🔄 Iniciando rollback de migración task_statuses y task_templates...")

        # Crear backup si se solicita
        if create_backup:
            print("📦 Creando backup de seguridad...")
            from scripts.backup_calendar_data import backup_calendar_data

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_calendar_data(
                output_dir=f"backups/pre_rollback_{timestamp}"
            )
            print(f"✅ Backup creado: {backup_file}")

        # Paso 1: Migrar status_id de vuelta a status (string)
        print("📝 Migrando status_id de vuelta a status...")
        db.execute(text("""
            UPDATE tasks
            SET status = CASE
                WHEN ts.name = 'Por Iniciar' THEN 'todo'
                WHEN ts.name = 'En Proceso' THEN 'in_progress'
                WHEN ts.name = 'Completado' THEN 'done'
                WHEN ts.name = 'Cancelado' THEN 'cancelled'
                WHEN ts.type = 'open' THEN 'todo'
                WHEN ts.type = 'in_progress' THEN 'in_progress'
                WHEN ts.type = 'closed' THEN 'done'
                ELSE 'todo'
            END
            FROM task_statuses ts
            WHERE tasks.status_id = ts.id
        """))
        db.commit()

        # Paso 2: Eliminar índices de tasks
        print("🗑️  Eliminando índices...")
        try:
            db.execute(text("DROP INDEX IF EXISTS idx_tasks_template_id"))
            db.execute(text("DROP INDEX IF EXISTS idx_tasks_board_order"))
            db.execute(text("DROP INDEX IF EXISTS idx_tasks_status_id"))
        except Exception as e:
            print(f"⚠️  Advertencia al eliminar índices: {e}")

        # Paso 3: Eliminar foreign keys
        print("🔗 Eliminando foreign keys...")
        try:
            db.execute(text("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS fk_tasks_template_id"))
            db.execute(text("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS fk_tasks_status_id"))
        except Exception as e:
            print(f"⚠️  Advertencia al eliminar constraints: {e}")

        # Paso 4: Eliminar columnas de tasks
        print("📊 Eliminando columnas de tasks...")
        db.execute(text("ALTER TABLE tasks DROP COLUMN IF EXISTS template_id"))
        db.execute(text("ALTER TABLE tasks DROP COLUMN IF EXISTS board_order"))
        db.execute(text("ALTER TABLE tasks DROP COLUMN IF EXISTS status_id"))
        db.commit()

        # Paso 5: Eliminar tablas
        print("🗑️  Eliminando tablas task_templates y task_statuses...")
        db.execute(text("DROP TABLE IF EXISTS task_templates CASCADE"))
        db.execute(text("DROP TABLE IF EXISTS task_statuses CASCADE"))
        db.commit()

        # Paso 6: Actualizar alembic_version
        print("📝 Actualizando alembic_version...")
        db.execute(text("""
            UPDATE alembic_version
            SET version_num = 'add_task_calendar_fields'
            WHERE version_num = 'add_task_statuses_templates'
        """))
        db.commit()

        print("✅ Rollback completado exitosamente")
        print("⚠️  Recuerda ejecutar las migraciones nuevamente si necesitas volver a aplicar los cambios")

    except Exception as e:
        print(f"❌ Error durante el rollback: {e}")
        db.rollback()
        raise

    finally:
        db.close()


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Rollback de migración task_statuses y task_templates"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="No crear backup antes del rollback (no recomendado)",
    )

    args = parser.parse_args()

    if args.no_backup:
        print("⚠️  ADVERTENCIA: Ejecutando sin backup de seguridad")
        confirm = input("¿Estás seguro? (escribe 'SI' para continuar): ")
        if confirm != "SI":
            print("❌ Rollback cancelado")
            return

    rollback_migration(create_backup=not args.no_backup)


if __name__ == "__main__":
    main()
