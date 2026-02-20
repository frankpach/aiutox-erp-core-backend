"""merge_user_task_statuses_head

Revision ID: 4c93b33c6441
Revises: add_approval_actions_fields, d5c1142871d9
Create Date: 2026-01-27 21:43:41.554707+00:00

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = '4c93b33c6441'
down_revision: str | None = ('add_approval_actions_fields', 'd5c1142871d9')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

