"""merge heads

Revision ID: 2026_01_16_merge_heads
Revises: add_tags_tables, 2025_01_22_theme_presets, add_deleted_at_to_files, add_comments_tables, 4ad0962434d7, add_crm_module, add_flow_runs_table, task_reminders_recurrences, 2026_01_16_teams, add_task_calendar_fields
Create Date: 2026-01-16 19:00:00.000000

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "2026_01_16_merge_heads"
down_revision: Sequence[str] | str | None = (
    "add_tags_tables",
    "2025_01_22_theme_presets",
    "add_deleted_at_to_files",
    "add_comments_tables",
    "4ad0962434d7",
    "add_crm_module",
    "add_flow_runs_table",
    "task_reminders_recurrences",
    "2026_01_16_teams",
    "add_task_calendar_fields",
)
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Merge heads - no schema changes."""


def downgrade() -> None:
    """Downgrade merge - no schema changes."""
