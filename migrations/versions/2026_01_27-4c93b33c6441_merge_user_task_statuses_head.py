"""merge_user_task_statuses_head

Revision ID: 4c93b33c6441
Revises: add_approval_actions_fields, d5c1142871d9
Create Date: 2026-01-27 21:43:41.554707+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c93b33c6441'
down_revision: Union[str, None] = ('add_approval_actions_fields', 'd5c1142871d9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

