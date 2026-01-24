"""Add user calendar preferences for auto-sync

Revision ID: 2026_01_23_002
Revises: 2026_01_23_001
Create Date: 2026-01-23 11:30:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_01_23_002'
down_revision = '2026_01_23_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tenant_id to user_calendar_preferences if table exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_calendar_preferences') THEN
                -- Add tenant_id column if it doesn't exist
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name = 'user_calendar_preferences'
                              AND column_name = 'tenant_id') THEN
                    ALTER TABLE user_calendar_preferences
                    ADD COLUMN tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE;
                    CREATE INDEX ix_user_calendar_preferences_tenant_id ON user_calendar_preferences(tenant_id);
                END IF;

                -- Add auto_sync_tasks column if it doesn't exist
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name = 'user_calendar_preferences'
                              AND column_name = 'auto_sync_tasks') THEN
                    ALTER TABLE user_calendar_preferences
                    ADD COLUMN auto_sync_tasks BOOLEAN NOT NULL DEFAULT FALSE;
                END IF;

                -- Add default_calendar_id column if it doesn't exist
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                              WHERE table_name = 'user_calendar_preferences'
                              AND column_name = 'default_calendar_id') THEN
                    ALTER TABLE user_calendar_preferences
                    ADD COLUMN default_calendar_id UUID;
                END IF;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove added columns
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_calendar_preferences') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'user_calendar_preferences'
                          AND column_name = 'default_calendar_id') THEN
                    ALTER TABLE user_calendar_preferences DROP COLUMN default_calendar_id;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'user_calendar_preferences'
                          AND column_name = 'auto_sync_tasks') THEN
                    ALTER TABLE user_calendar_preferences DROP COLUMN auto_sync_tasks;
                END IF;

                IF EXISTS (SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'user_calendar_preferences'
                          AND column_name = 'tenant_id') THEN
                    DROP INDEX IF EXISTS ix_user_calendar_preferences_tenant_id;
                    ALTER TABLE user_calendar_preferences DROP COLUMN tenant_id;
                END IF;
            END IF;
        END $$;
    """)
