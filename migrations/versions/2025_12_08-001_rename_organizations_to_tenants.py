"""Rename organizations to tenants

Revision ID: 001_rename_organizations_to_tenants
Revises: 001_add_auth_tables
Create Date: 2025-12-08 15:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_rename_orgs_to_tenants"
down_revision: str | None = "001_add_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename table organizations to tenants
    op.rename_table("organizations", "tenants")

    # Rename constraint
    op.execute("ALTER TABLE tenants RENAME CONSTRAINT uq_organizations_slug TO uq_tenants_slug")

    # Rename index
    op.execute("ALTER INDEX ix_organizations_slug RENAME TO ix_tenants_slug")

    # Rename column organization_id to tenant_id in users table
    # First, drop foreign key constraints that reference users
    op.execute("""
        ALTER TABLE user_roles
        DROP CONSTRAINT IF EXISTS user_roles_user_id_fkey,
        DROP CONSTRAINT IF EXISTS user_roles_granted_by_fkey;
    """)
    op.execute("""
        ALTER TABLE refresh_tokens
        DROP CONSTRAINT IF EXISTS refresh_tokens_user_id_fkey;
    """)

    # Rename users table to temporary table
    op.rename_table("users", "users_temp")

    # Create new users table with tenant_id
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            is_active BOOLEAN DEFAULT true NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)

    # Copy data from users_temp to users
    op.execute("""
        INSERT INTO users (id, email, password_hash, full_name, tenant_id, is_active, created_at, updated_at)
        SELECT id, email, password_hash, full_name, organization_id, is_active, created_at, updated_at
        FROM users_temp
    """)

    # Recreate foreign key constraints pointing to new users table
    op.execute("""
        ALTER TABLE user_roles
        ADD CONSTRAINT user_roles_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)
    op.execute("""
        ALTER TABLE user_roles
        ADD CONSTRAINT user_roles_granted_by_fkey
        FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL;
    """)
    op.execute("""
        ALTER TABLE refresh_tokens
        ADD CONSTRAINT refresh_tokens_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)

    # Now we can drop the temporary table
    op.drop_table("users_temp")

    # Rename index (if exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE indexname = 'ix_users_organization_id'
            ) THEN
                ALTER INDEX ix_users_organization_id RENAME TO ix_users_tenant_id;
            END IF;
        END $$;
    """)

    # Rename foreign key constraint (if exists)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'users_organization_id_fkey'
            ) THEN
                ALTER TABLE users RENAME CONSTRAINT users_organization_id_fkey TO users_tenant_id_fkey;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Reverse the changes
    op.rename_table("tenants", "organizations")
    op.execute("ALTER TABLE organizations RENAME CONSTRAINT uq_tenants_slug TO uq_organizations_slug")
    op.execute("ALTER INDEX ix_tenants_slug RENAME TO ix_organizations_slug")

    # Rename column back
    # First, drop foreign key constraints that reference users
    op.execute("""
        ALTER TABLE user_roles
        DROP CONSTRAINT IF EXISTS user_roles_user_id_fkey,
        DROP CONSTRAINT IF EXISTS user_roles_granted_by_fkey;
    """)
    op.execute("""
        ALTER TABLE refresh_tokens
        DROP CONSTRAINT IF EXISTS refresh_tokens_user_id_fkey;
    """)

    # Rename users table to temporary table
    op.rename_table("users", "users_temp")

    # Create new users table with organization_id
    op.execute("""
        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            is_active BOOLEAN DEFAULT true NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)

    # Copy data from users_temp to users
    op.execute("""
        INSERT INTO users (id, email, password_hash, full_name, organization_id, is_active, created_at, updated_at)
        SELECT id, email, password_hash, full_name, tenant_id, is_active, created_at, updated_at
        FROM users_temp
    """)

    # Recreate foreign key constraints pointing to new users table
    op.execute("""
        ALTER TABLE user_roles
        ADD CONSTRAINT user_roles_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)
    op.execute("""
        ALTER TABLE user_roles
        ADD CONSTRAINT user_roles_granted_by_fkey
        FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL;
    """)
    op.execute("""
        ALTER TABLE refresh_tokens
        ADD CONSTRAINT refresh_tokens_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)

    # Now we can drop the temporary table
    op.drop_table("users_temp")

    op.execute("ALTER INDEX ix_users_tenant_id RENAME TO ix_users_organization_id")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'users_tenant_id_fkey'
            ) THEN
                ALTER TABLE users RENAME CONSTRAINT users_tenant_id_fkey TO users_organization_id_fkey;
            END IF;
        END $$;
    """)
