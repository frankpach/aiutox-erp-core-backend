"""Merge task_assign_audit and task_statuses_templates

Revision ID: 5ce9e0cd34fc
Revises: 2026_01_17_task_assign_audit, add_task_statuses_templates
Create Date: 2026-01-20 15:07:31.467053+00:00

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '5ce9e0cd34fc'
down_revision: str | None = ('2026_01_17_task_assign_audit', 'add_task_statuses_templates')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

