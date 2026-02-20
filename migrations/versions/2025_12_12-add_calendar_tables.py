"""Add calendar tables: calendars, calendar_events, event_attendees, event_reminders

Revision ID: add_calendar_tables
Revises: add_integrations_tables
Create Date: 2025-12-12 00:00:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_calendar_tables"
down_revision: str | None = "add_integrations_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create calendars table
    op.create_table(
        "calendars",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("calendar_type", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendars_tenant_id", "calendars", ["tenant_id"], unique=False)
    op.create_index("ix_calendars_owner_id", "calendars", ["owner_id"], unique=False)
    op.create_index("ix_calendars_organization_id", "calendars", ["organization_id"], unique=False)
    op.create_index("idx_calendars_tenant_owner", "calendars", ["tenant_id", "owner_id"], unique=False)
    op.create_index("idx_calendars_organization", "calendars", ["tenant_id", "organization_id"], unique=False)

    # Create calendar_events table
    op.create_table(
        "calendar_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calendar_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("start_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_time", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("recurrence_type", sa.String(length=20), nullable=False, server_default="none"),
        sa.Column("recurrence_end_date", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("recurrence_count", sa.Integer(), nullable=True),
        sa.Column("recurrence_interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("recurrence_days_of_week", sa.String(length=20), nullable=True),
        sa.Column("recurrence_day_of_month", sa.Integer(), nullable=True),
        sa.Column("recurrence_month_of_year", sa.Integer(), nullable=True),
        sa.Column("organizer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["calendar_id"], ["calendars.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calendar_events_tenant_id", "calendar_events", ["tenant_id"], unique=False)
    op.create_index("ix_calendar_events_calendar_id", "calendar_events", ["calendar_id"], unique=False)
    op.create_index("ix_calendar_events_start_time", "calendar_events", ["start_time"], unique=False)
    op.create_index("ix_calendar_events_end_time", "calendar_events", ["end_time"], unique=False)
    op.create_index("ix_calendar_events_status", "calendar_events", ["status"], unique=False)
    op.create_index("ix_calendar_events_organizer_id", "calendar_events", ["organizer_id"], unique=False)
    op.create_index("idx_events_calendar_time", "calendar_events", ["calendar_id", "start_time"], unique=False)
    op.create_index("idx_events_tenant_time", "calendar_events", ["tenant_id", "start_time", "end_time"], unique=False)
    op.create_index("idx_events_status", "calendar_events", ["tenant_id", "status"], unique=False)

    # Create event_attendees table
    op.create_table(
        "event_attendees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("response_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_attendees_tenant_id", "event_attendees", ["tenant_id"], unique=False)
    op.create_index("ix_event_attendees_event_id", "event_attendees", ["event_id"], unique=False)
    op.create_index("ix_event_attendees_user_id", "event_attendees", ["user_id"], unique=False)
    op.create_index("ix_event_attendees_status", "event_attendees", ["status"], unique=False)
    op.create_index("idx_attendees_event_user", "event_attendees", ["event_id", "user_id"], unique=False)
    op.create_index("idx_attendees_status", "event_attendees", ["event_id", "status"], unique=False)

    # Create event_reminders table
    op.create_table(
        "event_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reminder_type", sa.String(length=20), nullable=False),
        sa.Column("minutes_before", sa.Integer(), nullable=False),
        sa.Column("sent_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("is_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["calendar_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_reminders_tenant_id", "event_reminders", ["tenant_id"], unique=False)
    op.create_index("ix_event_reminders_event_id", "event_reminders", ["event_id"], unique=False)
    op.create_index("ix_event_reminders_is_sent", "event_reminders", ["is_sent"], unique=False)
    op.create_index("idx_reminders_event_sent", "event_reminders", ["event_id", "is_sent"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_reminders_event_sent", table_name="event_reminders")
    op.drop_index("ix_event_reminders_is_sent", table_name="event_reminders")
    op.drop_index("ix_event_reminders_event_id", table_name="event_reminders")
    op.drop_index("ix_event_reminders_tenant_id", table_name="event_reminders")
    op.drop_table("event_reminders")

    op.drop_index("idx_attendees_status", table_name="event_attendees")
    op.drop_index("idx_attendees_event_user", table_name="event_attendees")
    op.drop_index("ix_event_attendees_status", table_name="event_attendees")
    op.drop_index("ix_event_attendees_user_id", table_name="event_attendees")
    op.drop_index("ix_event_attendees_event_id", table_name="event_attendees")
    op.drop_index("ix_event_attendees_tenant_id", table_name="event_attendees")
    op.drop_table("event_attendees")

    op.drop_index("idx_events_status", table_name="calendar_events")
    op.drop_index("idx_events_tenant_time", table_name="calendar_events")
    op.drop_index("idx_events_calendar_time", table_name="calendar_events")
    op.drop_index("ix_calendar_events_organizer_id", table_name="calendar_events")
    op.drop_index("ix_calendar_events_status", table_name="calendar_events")
    op.drop_index("ix_calendar_events_end_time", table_name="calendar_events")
    op.drop_index("ix_calendar_events_start_time", table_name="calendar_events")
    op.drop_index("ix_calendar_events_calendar_id", table_name="calendar_events")
    op.drop_index("ix_calendar_events_tenant_id", table_name="calendar_events")
    op.drop_table("calendar_events")

    op.drop_index("idx_calendars_organization", table_name="calendars")
    op.drop_index("idx_calendars_tenant_owner", table_name="calendars")
    op.drop_index("ix_calendars_organization_id", table_name="calendars")
    op.drop_index("ix_calendars_owner_id", table_name="calendars")
    op.drop_index("ix_calendars_tenant_id", table_name="calendars")
    op.drop_table("calendars")








