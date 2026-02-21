"""fix_automation_executions_unique_constraint

Change the unique index on automation_executions.event_id to be on
(rule_id, event_id) so multiple rules can process the same event.

Revision ID: dd4439c2fee5
Revises: 78ef2625a0a4
Create Date: 2026-02-21 05:37:58.014649+00:00
"""

from alembic import op

revision: str = "dd4439c2fee5"
down_revision: str | None = "78ef2625a0a4"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_index("ix_automation_executions_event_id", table_name="automation_executions")
    op.create_index(
        "idx_automation_executions_rule_event",
        "automation_executions",
        ["rule_id", "event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_automation_executions_rule_event", table_name="automation_executions")
    op.create_index(
        "ix_automation_executions_event_id",
        "automation_executions",
        ["event_id"],
        unique=True,
    )
