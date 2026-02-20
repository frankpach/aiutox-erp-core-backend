from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.core.exceptions import raise_bad_request, raise_not_found
from app.modules.inventory.repositories.inventory_repository import InventoryRepository


class InventoryService:
    def __init__(self, db):
        self.repository = InventoryRepository(db)

    # Warehouses
    def create_warehouse(self, tenant_id: UUID, data: dict):
        return self.repository.create_warehouse({**data, "tenant_id": tenant_id})

    def list_warehouses(self, tenant_id: UUID, skip: int = 0, limit: int = 100):
        return self.repository.list_warehouses(
            tenant_id=tenant_id, skip=skip, limit=limit
        )

    def get_warehouse(self, tenant_id: UUID, warehouse_id: UUID):
        warehouse = self.repository.get_warehouse(
            warehouse_id=warehouse_id, tenant_id=tenant_id
        )
        if not warehouse:
            raise_not_found("Warehouse", str(warehouse_id))
        return warehouse

    def update_warehouse(self, tenant_id: UUID, warehouse_id: UUID, data: dict):
        warehouse = self.get_warehouse(tenant_id=tenant_id, warehouse_id=warehouse_id)
        return self.repository.update_warehouse(warehouse, data)

    def delete_warehouse(self, tenant_id: UUID, warehouse_id: UUID):
        warehouse = self.get_warehouse(tenant_id=tenant_id, warehouse_id=warehouse_id)
        self.repository.delete_warehouse(warehouse)

    # Locations
    def create_location(self, tenant_id: UUID, warehouse_id: UUID, data: dict):
        self.get_warehouse(tenant_id=tenant_id, warehouse_id=warehouse_id)
        return self.repository.create_location(
            {**data, "tenant_id": tenant_id, "warehouse_id": warehouse_id}
        )

    def list_locations(
        self,
        tenant_id: UUID,
        warehouse_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return self.repository.list_locations(
            tenant_id=tenant_id, warehouse_id=warehouse_id, skip=skip, limit=limit
        )

    def get_location(self, tenant_id: UUID, location_id: UUID):
        location = self.repository.get_location(
            location_id=location_id, tenant_id=tenant_id
        )
        if not location:
            raise_not_found("Location", str(location_id))
        return location

    def update_location(self, tenant_id: UUID, location_id: UUID, data: dict):
        location = self.get_location(tenant_id=tenant_id, location_id=location_id)
        return self.repository.update_location(location, data)

    def delete_location(self, tenant_id: UUID, location_id: UUID):
        location = self.get_location(tenant_id=tenant_id, location_id=location_id)
        self.repository.delete_location(location)

    # Stock moves
    def create_stock_move(self, tenant_id: UUID, user_id: UUID, data: dict):
        from_location_id = data.get("from_location_id")
        to_location_id = data.get("to_location_id")

        if not from_location_id and not to_location_id:
            raise_bad_request(
                "INVALID_STOCK_MOVE",
                "Stock move requires at least one of from_location_id or to_location_id",
            )

        if from_location_id:
            self.get_location(tenant_id=tenant_id, location_id=from_location_id)
        if to_location_id:
            self.get_location(tenant_id=tenant_id, location_id=to_location_id)

        qty: Decimal = data.get("quantity")
        if qty == 0:
            raise_bad_request("INVALID_STOCK_MOVE", "Quantity must be non-zero")

        return self.repository.create_stock_move(
            {**data, "tenant_id": tenant_id, "created_by": user_id}
        )

    def list_stock_moves(
        self,
        tenant_id: UUID,
        product_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return self.repository.list_stock_moves(
            tenant_id=tenant_id, product_id=product_id, skip=skip, limit=limit
        )
