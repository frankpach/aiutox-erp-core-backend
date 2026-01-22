"""Merge task_assign_audit and task_statuses_templates

Revision ID: 5ce9e0cd34fc
Revises: 2026_01_17_task_assign_audit, add_task_statuses_templates
Create Date: 2026-01-20 15:07:31.467053+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ce9e0cd34fc'
down_revision: Union[str, None] = ('2026_01_17_task_assign_audit', 'add_task_statuses_templates')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

