"""Add inventory module tables: warehouses, locations, stock_moves

Revision ID: add_inventory_module
Revises: add_products_module
Create Date: 2026-01-04 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_inventory_module"
down_revision: str | None = "add_products_module"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_warehouses_tenant_code"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_warehouses_tenant_name"),
    )
    op.create_index("ix_warehouses_tenant_id", "warehouses", ["tenant_id"], unique=False)
    op.create_index("ix_warehouses_code", "warehouses", ["code"], unique=False)
    op.create_index(
        "idx_warehouses_tenant_name",
        "warehouses",
        ["tenant_id", "name"],
        unique=False,
    )

    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("warehouse_id", "code", name="uq_locations_warehouse_code"),
    )
    op.create_index("ix_locations_tenant_id", "locations", ["tenant_id"], unique=False)
    op.create_index("ix_locations_warehouse_id", "locations", ["warehouse_id"], unique=False)
    op.create_index("ix_locations_code", "locations", ["code"], unique=False)
    op.create_index(
        "idx_locations_tenant_warehouse",
        "locations",
        ["tenant_id", "warehouse_id"],
        unique=False,
    )

    op.create_table(
        "stock_moves",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("move_type", sa.String(length=30), nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("quantity <> 0", name="ck_stock_moves_quantity_nonzero"),
    )
    op.create_index("ix_stock_moves_tenant_id", "stock_moves", ["tenant_id"], unique=False)
    op.create_index("ix_stock_moves_product_id", "stock_moves", ["product_id"], unique=False)
    op.create_index(
        "ix_stock_moves_from_location_id",
        "stock_moves",
        ["from_location_id"],
        unique=False,
    )
    op.create_index(
        "ix_stock_moves_to_location_id",
        "stock_moves",
        ["to_location_id"],
        unique=False,
    )
    op.create_index("ix_stock_moves_move_type", "stock_moves", ["move_type"], unique=False)
    op.create_index(
        "idx_stock_moves_tenant_created_at",
        "stock_moves",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_stock_moves_tenant_created_at", table_name="stock_moves")
    op.drop_index("ix_stock_moves_move_type", table_name="stock_moves")
    op.drop_index("ix_stock_moves_to_location_id", table_name="stock_moves")
    op.drop_index("ix_stock_moves_from_location_id", table_name="stock_moves")
    op.drop_index("ix_stock_moves_product_id", table_name="stock_moves")
    op.drop_index("ix_stock_moves_tenant_id", table_name="stock_moves")
    op.drop_table("stock_moves")

    op.drop_index("idx_locations_tenant_warehouse", table_name="locations")
    op.drop_index("ix_locations_code", table_name="locations")
    op.drop_index("ix_locations_warehouse_id", table_name="locations")
    op.drop_index("ix_locations_tenant_id", table_name="locations")
    op.drop_table("locations")

    op.drop_index("idx_warehouses_tenant_name", table_name="warehouses")
    op.drop_index("ix_warehouses_code", table_name="warehouses")
    op.drop_index("ix_warehouses_tenant_id", table_name="warehouses")
    op.drop_table("warehouses")
