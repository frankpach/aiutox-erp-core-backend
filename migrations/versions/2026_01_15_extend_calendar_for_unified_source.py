"""Extend calendar models for unified source and resources

Revision ID: extend_calendar_unified_source
Revises: add_task_source_fields
Create Date: 2026-01-15 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "extend_calendar_unified_source"
down_revision: str | None = "add_calendar_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = "add_task_source_fields"


def upgrade() -> None:
    # Extend calendar_events table with unified source fields
    op.add_column(
        "calendar_events",
        sa.Column("source_type", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_calendar_events_source_type", "calendar_events", ["source_type"], unique=False)

    op.add_column(
        "calendar_events",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_calendar_events_source_id", "calendar_events", ["source_id"], unique=False)

    # External integration fields
    op.add_column(
        "calendar_events",
        sa.Column("provider", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_calendar_events_provider", "calendar_events", ["provider"], unique=False)

    op.add_column(
        "calendar_events",
        sa.Column("external_id", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_calendar_events_external_id", "calendar_events", ["external_id"], unique=False)

    op.add_column(
        "calendar_events",
        sa.Column("read_only", sa.Boolean(), nullable=False, server_default="false"),
    )

    # RRULE support for advanced recurrence
    op.add_column(
        "calendar_events",
        sa.Column("recurrence_rule", sa.Text(), nullable=True),
    )

    op.add_column(
        "calendar_events",
        sa.Column("recurrence_exdates", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Composite index for source lookup
    op.create_index(
        "idx_calendar_events_source",
        "calendar_events",
        ["source_type", "source_id"],
        unique=False,
    )

    # Composite index for external events
    op.create_index(
        "idx_calendar_events_external",
        "calendar_events",
        ["provider", "external_id"],
        unique=False,
    )

    # Create calendar_resources table for scheduler view
    op.create_table(
        "calendar_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "calendar_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["calendar_id"],
            ["calendars.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_calendar_resources_tenant_id", "calendar_resources", ["tenant_id"], unique=False)
    op.create_index("ix_calendar_resources_calendar_id", "calendar_resources", ["calendar_id"], unique=False)
    op.create_index("ix_calendar_resources_resource_type", "calendar_resources", ["resource_type"], unique=False)
    op.create_index(
        "idx_calendar_resources_tenant_type",
        "calendar_resources",
        ["tenant_id", "resource_type"],
        unique=False,
    )

    # Create event_resources junction table (many-to-many)
    op.create_table(
        "event_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["calendar_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["calendar_resources.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_event_resources_tenant_id", "event_resources", ["tenant_id"], unique=False)
    op.create_index("ix_event_resources_event_id", "event_resources", ["event_id"], unique=False)
    op.create_index("ix_event_resources_resource_id", "event_resources", ["resource_id"], unique=False)
    op.create_index(
        "idx_event_resources_unique",
        "event_resources",
        ["event_id", "resource_id"],
        unique=True,
    )


def downgrade() -> None:
    # Drop event_resources table
    op.drop_index("idx_event_resources_unique", table_name="event_resources")
    op.drop_index("ix_event_resources_resource_id", table_name="event_resources")
    op.drop_index("ix_event_resources_event_id", table_name="event_resources")
    op.drop_index("ix_event_resources_tenant_id", table_name="event_resources")
    op.drop_table("event_resources")

    # Drop calendar_resources table
    op.drop_index("idx_calendar_resources_tenant_type", table_name="calendar_resources")
    op.drop_index("ix_calendar_resources_resource_type", table_name="calendar_resources")
    op.drop_index("ix_calendar_resources_calendar_id", table_name="calendar_resources")
    op.drop_index("ix_calendar_resources_tenant_id", table_name="calendar_resources")
    op.drop_table("calendar_resources")

    # Drop calendar_events extensions
    op.drop_index("idx_calendar_events_external", table_name="calendar_events")
    op.drop_index("idx_calendar_events_source", table_name="calendar_events")
    op.drop_column("calendar_events", "recurrence_exdates")
    op.drop_column("calendar_events", "recurrence_rule")
    op.drop_column("calendar_events", "read_only")
    op.drop_index("ix_calendar_events_external_id", table_name="calendar_events")
    op.drop_column("calendar_events", "external_id")
    op.drop_index("ix_calendar_events_provider", table_name="calendar_events")
    op.drop_column("calendar_events", "provider")
    op.drop_index("ix_calendar_events_source_id", table_name="calendar_events")
    op.drop_column("calendar_events", "source_id")
    op.drop_index("ix_calendar_events_source_type", table_name="calendar_events")
    op.drop_column("calendar_events", "source_type")
