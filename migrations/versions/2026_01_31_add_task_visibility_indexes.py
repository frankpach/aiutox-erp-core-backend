"""add task visibility indexes

Revision ID: 2026_01_31_add_task_visibility_indexes
Revises: 2026_03_05_optimize_task_indexes
Create Date: 2026-01-31 15:00:00.000000

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "2026_01_31_add_task_visibility_indexes"
down_revision = "2026_03_05_optimize_task_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Agrega índices específicos para optimizar get_visible_tasks."""

    # Índice compuesto principal para visibilidad de tareas
    # Optimiza: WHERE tenant_id = ? AND (created_by_id = ? OR assigned_to_id = ?)
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant_user_visibility ON tasks (tenant_id, created_by_id, assigned_to_id)")

    # Índice para task assignments lookup
    # Optimiza: JOIN task_assignments WHERE task_id = ? AND tenant_id = ? AND assigned_to_id = ?
    op.execute("CREATE INDEX IF NOT EXISTS idx_task_assignments_lookup ON task_assignments (task_id, tenant_id, assigned_to_id)")

    # Índice para filtrar por tenant y user_id en task_assignments
    # Optimiza queries de asignaciones por usuario
    op.execute("CREATE INDEX IF NOT EXISTS idx_task_assignments_tenant_user ON task_assignments (tenant_id, assigned_to_id)")

    # Índice para filtrar por tenant y status
    # Simple index sin condición WHERE
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant_status ON tasks (tenant_id, status)")

    # Analizar tablas para actualizar estadísticas
    op.execute("ANALYZE tasks;")
    op.execute("ANALYZE task_assignments;")


def downgrade() -> None:
    """Elimina los índices de visibilidad."""

    op.drop_index("idx_tasks_tenant_user_visibility", table_name="tasks")
    op.drop_index("idx_task_assignments_lookup", table_name="task_assignments")
    op.drop_index("idx_task_assignments_tenant_user", table_name="task_assignments")
    op.drop_index("idx_tasks_tenant_status", table_name="tasks")
