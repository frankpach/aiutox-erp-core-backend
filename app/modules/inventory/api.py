from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.db.deps import get_db
from app.models.user import User
from app.modules.inventory.schemas.inventory import (
  LocationCreate,
  LocationResponse,
  LocationUpdate,
  StockMoveCreate,
  StockMoveResponse,
  WarehouseCreate,
  WarehouseResponse,
  WarehouseUpdate,
)
from app.modules.inventory.services.inventory_service import InventoryService
from app.schemas.common import PaginationMeta, StandardListResponse, StandardResponse

router = APIRouter()


def get_inventory_service(db: Annotated[Session, Depends(get_db)]) -> InventoryService:
  return InventoryService(db)


@router.get(
  "/warehouses",
  response_model=StandardListResponse[WarehouseResponse],
  status_code=status.HTTP_200_OK,
  summary="List warehouses",
  description="List warehouses. Requires inventory.view permission.",
)
async def list_warehouses(
  current_user: Annotated[User, Depends(require_permission("inventory.view"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
  page: int = Query(default=1, ge=1),
  page_size: int = Query(default=20, ge=1, le=100),
) -> StandardListResponse[WarehouseResponse]:
  skip = (page - 1) * page_size
  warehouses = service.list_warehouses(current_user.tenant_id, skip=skip, limit=page_size)
  total = len(warehouses)
  total_pages = (total + page_size - 1) // page_size if total > 0 else 0
  return StandardListResponse(
    data=[WarehouseResponse.model_validate(w) for w in warehouses],
    meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
  )


@router.post(
  "/warehouses",
  response_model=StandardResponse[WarehouseResponse],
  status_code=status.HTTP_201_CREATED,
  summary="Create warehouse",
  description="Create warehouse. Requires inventory.edit permission.",
)
async def create_warehouse(
  payload: WarehouseCreate,
  current_user: Annotated[User, Depends(require_permission("inventory.edit"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StandardResponse[WarehouseResponse]:
  warehouse = service.create_warehouse(current_user.tenant_id, payload.model_dump())
  return StandardResponse(data=WarehouseResponse.model_validate(warehouse))


@router.get(
  "/warehouses/{warehouse_id}",
  response_model=StandardResponse[WarehouseResponse],
  status_code=status.HTTP_200_OK,
  summary="Get warehouse",
  description="Get warehouse. Requires inventory.view permission.",
)
async def get_warehouse(
  warehouse_id: Annotated[UUID, Path(...)],
  current_user: Annotated[User, Depends(require_permission("inventory.view"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StandardResponse[WarehouseResponse]:
  warehouse = service.get_warehouse(current_user.tenant_id, warehouse_id)
  return StandardResponse(data=WarehouseResponse.model_validate(warehouse))


@router.put(
  "/warehouses/{warehouse_id}",
  response_model=StandardResponse[WarehouseResponse],
  status_code=status.HTTP_200_OK,
  summary="Update warehouse",
  description="Update warehouse. Requires inventory.edit permission.",
)
async def update_warehouse(
  warehouse_id: Annotated[UUID, Path(...)],
  payload: WarehouseUpdate,
  current_user: Annotated[User, Depends(require_permission("inventory.edit"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StandardResponse[WarehouseResponse]:
  warehouse = service.update_warehouse(
    tenant_id=current_user.tenant_id,
    warehouse_id=warehouse_id,
    data=payload.model_dump(exclude_unset=True),
  )
  return StandardResponse(data=WarehouseResponse.model_validate(warehouse))


@router.delete(
  "/warehouses/{warehouse_id}",
  status_code=status.HTTP_204_NO_CONTENT,
  summary="Delete warehouse",
  description="Delete warehouse. Requires inventory.edit permission.",
)
async def delete_warehouse(
  warehouse_id: Annotated[UUID, Path(...)],
  current_user: Annotated[User, Depends(require_permission("inventory.edit"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> None:
  service.delete_warehouse(current_user.tenant_id, warehouse_id)


@router.get(
  "/warehouses/{warehouse_id}/locations",
  response_model=StandardListResponse[LocationResponse],
  status_code=status.HTTP_200_OK,
  summary="List locations",
  description="List locations for a warehouse. Requires inventory.view permission.",
)
async def list_locations(
  warehouse_id: Annotated[UUID, Path(...)],
  current_user: Annotated[User, Depends(require_permission("inventory.view"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
  page: int = Query(default=1, ge=1),
  page_size: int = Query(default=20, ge=1, le=100),
) -> StandardListResponse[LocationResponse]:
  skip = (page - 1) * page_size
  locations = service.list_locations(current_user.tenant_id, warehouse_id=warehouse_id, skip=skip, limit=page_size)
  total = len(locations)
  total_pages = (total + page_size - 1) // page_size if total > 0 else 0
  return StandardListResponse(
    data=[LocationResponse.model_validate(location) for location in locations],
    meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
  )


@router.post(
  "/warehouses/{warehouse_id}/locations",
  response_model=StandardResponse[LocationResponse],
  status_code=status.HTTP_201_CREATED,
  summary="Create location",
  description="Create location. Requires inventory.edit permission.",
)
async def create_location(
  warehouse_id: Annotated[UUID, Path(...)],
  payload: LocationCreate,
  current_user: Annotated[User, Depends(require_permission("inventory.edit"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StandardResponse[LocationResponse]:
  location = service.create_location(current_user.tenant_id, warehouse_id, payload.model_dump())
  return StandardResponse(data=LocationResponse.model_validate(location))


@router.get(
  "/locations/{location_id}",
  response_model=StandardResponse[LocationResponse],
  status_code=status.HTTP_200_OK,
  summary="Get location",
  description="Get location. Requires inventory.view permission.",
)
async def get_location(
  location_id: Annotated[UUID, Path(...)],
  current_user: Annotated[User, Depends(require_permission("inventory.view"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StandardResponse[LocationResponse]:
  location = service.get_location(current_user.tenant_id, location_id)
  return StandardResponse(data=LocationResponse.model_validate(location))


@router.put(
  "/locations/{location_id}",
  response_model=StandardResponse[LocationResponse],
  status_code=status.HTTP_200_OK,
  summary="Update location",
  description="Update location. Requires inventory.edit permission.",
)
async def update_location(
  location_id: Annotated[UUID, Path(...)],
  payload: LocationUpdate,
  current_user: Annotated[User, Depends(require_permission("inventory.edit"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StandardResponse[LocationResponse]:
  location = service.update_location(
    tenant_id=current_user.tenant_id,
    location_id=location_id,
    data=payload.model_dump(exclude_unset=True),
  )
  return StandardResponse(data=LocationResponse.model_validate(location))


@router.delete(
  "/locations/{location_id}",
  status_code=status.HTTP_204_NO_CONTENT,
  summary="Delete location",
  description="Delete location. Requires inventory.edit permission.",
)
async def delete_location(
  location_id: Annotated[UUID, Path(...)],
  current_user: Annotated[User, Depends(require_permission("inventory.edit"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> None:
  service.delete_location(current_user.tenant_id, location_id)


@router.get(
  "/stock-moves",
  response_model=StandardListResponse[StockMoveResponse],
  status_code=status.HTTP_200_OK,
  summary="List stock moves",
  description="List stock moves. Requires inventory.view permission.",
)
async def list_stock_moves(
  current_user: Annotated[User, Depends(require_permission("inventory.view"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
  product_id: UUID | None = Query(default=None),
  page: int = Query(default=1, ge=1),
  page_size: int = Query(default=20, ge=1, le=100),
) -> StandardListResponse[StockMoveResponse]:
  skip = (page - 1) * page_size
  moves = service.list_stock_moves(current_user.tenant_id, product_id=product_id, skip=skip, limit=page_size)
  total = len(moves)
  total_pages = (total + page_size - 1) // page_size if total > 0 else 0
  return StandardListResponse(
    data=[StockMoveResponse.model_validate(m) for m in moves],
    meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
  )


@router.post(
  "/stock-moves",
  response_model=StandardResponse[StockMoveResponse],
  status_code=status.HTTP_201_CREATED,
  summary="Create stock move",
  description="Create stock move. Requires inventory.adjust_stock permission.",
)
async def create_stock_move(
  payload: StockMoveCreate,
  current_user: Annotated[User, Depends(require_permission("inventory.adjust_stock"))],
  service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StandardResponse[StockMoveResponse]:
  move = service.create_stock_move(
    tenant_id=current_user.tenant_id,
    user_id=current_user.id,
    data=payload.model_dump(),
  )
  return StandardResponse(data=StockMoveResponse.model_validate(move))
