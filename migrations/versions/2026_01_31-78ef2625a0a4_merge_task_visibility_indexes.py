"""merge_task_visibility_indexes

Revision ID: 78ef2625a0a4
Revises: 4c93b33c6441, 20260131_task_visibility_idx
Create Date: 2026-01-31 19:53:26.348356+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78ef2625a0a4'
down_revision: Union[str, None] = ('4c93b33c6441', '20260131_task_visibility_idx')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

