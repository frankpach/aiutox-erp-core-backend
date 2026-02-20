"""optimize task indexes

Revision ID: 2026_03_05_optimize_task_indexes
Revises: 2026_01_23_add_task_dependencies_and_resources
Create Date: 2026-03-05 10:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '2026_03_05_optimize_task_indexes'
down_revision = '2026_01_24_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Agrega índices compuestos para optimizar queries más frecuentes."""

    # Índice para queries filtrados por tenant, status y fecha de creación
    op.create_index(
        'idx_tasks_tenant_status_created',
        'tasks',
        ['tenant_id', 'status', 'created_at'],
        unique=False
    )

    # Índice para queries de tareas asignadas con fecha de vencimiento
    # Solo indexa tareas que tienen due_date
    op.execute("""
        CREATE INDEX idx_tasks_tenant_assigned_due
        ON tasks (tenant_id, assigned_to_id, due_date)
        WHERE due_date IS NOT NULL
    """)

    # Índice para queries de tareas creadas desde templates
    # Solo indexa tareas que tienen template_id
    op.execute("""
        CREATE INDEX idx_tasks_tenant_template
        ON tasks (tenant_id, template_id)
        WHERE template_id IS NOT NULL
    """)

    # Índice para búsqueda por prioridad y estado
    op.create_index(
        'idx_tasks_tenant_priority_status',
        'tasks',
        ['tenant_id', 'priority', 'status'],
        unique=False
    )

    # Índice para tareas con fechas de inicio
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_tenant_start_at
        ON tasks (tenant_id, start_at)
        WHERE start_at IS NOT NULL
    """)

    # Analizar tablas para actualizar estadísticas del query planner
    op.execute("ANALYZE tasks;")
    op.execute("ANALYZE task_statuses;")
    op.execute("ANALYZE task_templates;")
    op.execute("ANALYZE task_dependencies;")
    op.execute("ANALYZE task_resources;")


def downgrade() -> None:
    """Elimina los índices optimizados."""

    op.drop_index('idx_tasks_tenant_status_created', table_name='tasks')
    op.drop_index('idx_tasks_tenant_assigned_due', table_name='tasks')
    op.drop_index('idx_tasks_tenant_template', table_name='tasks')
    op.drop_index('idx_tasks_tenant_priority_status', table_name='tasks')
    op.execute("DROP INDEX IF EXISTS idx_tasks_tenant_start_at")
