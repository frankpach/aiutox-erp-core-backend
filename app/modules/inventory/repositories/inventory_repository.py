from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.inventory.models.inventory import Location, StockMove, Warehouse


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    # Warehouses
    def create_warehouse(self, data: dict) -> Warehouse:
        warehouse = Warehouse(**data)
        self.db.add(warehouse)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def list_warehouses(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Warehouse]:
        return (
            self.db.query(Warehouse)
            .filter(Warehouse.tenant_id == tenant_id)
            .order_by(Warehouse.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_warehouse(self, warehouse_id: UUID, tenant_id: UUID) -> Warehouse | None:
        return (
            self.db.query(Warehouse)
            .filter(Warehouse.id == warehouse_id, Warehouse.tenant_id == tenant_id)
            .first()
        )

    def update_warehouse(self, warehouse: Warehouse, data: dict) -> Warehouse:
        for key, value in data.items():
            setattr(warehouse, key, value)
        self.db.commit()
        self.db.refresh(warehouse)
        return warehouse

    def delete_warehouse(self, warehouse: Warehouse) -> None:
        self.db.delete(warehouse)
        self.db.commit()

    # Locations
    def create_location(self, data: dict) -> Location:
        location = Location(**data)
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    def list_locations(
        self,
        tenant_id: UUID,
        warehouse_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Location]:
        query = self.db.query(Location).filter(Location.tenant_id == tenant_id)
        if warehouse_id:
            query = query.filter(Location.warehouse_id == warehouse_id)
        return (
            query.order_by(Location.created_at.desc()).offset(skip).limit(limit).all()
        )

    def get_location(self, location_id: UUID, tenant_id: UUID) -> Location | None:
        return (
            self.db.query(Location)
            .filter(Location.id == location_id, Location.tenant_id == tenant_id)
            .first()
        )

    def update_location(self, location: Location, data: dict) -> Location:
        for key, value in data.items():
            setattr(location, key, value)
        self.db.commit()
        self.db.refresh(location)
        return location

    def delete_location(self, location: Location) -> None:
        self.db.delete(location)
        self.db.commit()

    # Stock moves
    def create_stock_move(self, data: dict) -> StockMove:
        move = StockMove(**data)
        self.db.add(move)
        self.db.commit()
        self.db.refresh(move)
        return move

    def list_stock_moves(
        self,
        tenant_id: UUID,
        product_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[StockMove]:
        query = self.db.query(StockMove).filter(StockMove.tenant_id == tenant_id)
        if product_id:
            query = query.filter(StockMove.product_id == product_id)
        return (
            query.order_by(StockMove.created_at.desc()).offset(skip).limit(limit).all()
        )
