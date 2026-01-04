from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WarehouseBase(BaseModel):
  name: str = Field(..., min_length=1, max_length=255)
  code: str = Field(..., min_length=1, max_length=50)
  description: str | None = None


class WarehouseCreate(WarehouseBase):
  pass


class WarehouseUpdate(BaseModel):
  name: str | None = Field(None, min_length=1, max_length=255)
  code: str | None = Field(None, min_length=1, max_length=50)
  description: str | None = None


class WarehouseResponse(WarehouseBase):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  tenant_id: UUID
  created_at: datetime
  updated_at: datetime


class LocationBase(BaseModel):
  name: str = Field(..., min_length=1, max_length=255)
  code: str = Field(..., min_length=1, max_length=50)
  description: str | None = None


class LocationCreate(LocationBase):
  pass


class LocationUpdate(BaseModel):
  name: str | None = Field(None, min_length=1, max_length=255)
  code: str | None = Field(None, min_length=1, max_length=50)
  description: str | None = None


class LocationResponse(LocationBase):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  tenant_id: UUID
  warehouse_id: UUID
  created_at: datetime
  updated_at: datetime


class StockMoveCreate(BaseModel):
  product_id: UUID
  from_location_id: UUID | None = None
  to_location_id: UUID | None = None
  quantity: Decimal
  unit_cost: Decimal | None = None
  move_type: str = Field(..., min_length=1, max_length=30)
  reference: str | None = Field(None, max_length=255)


class StockMoveResponse(BaseModel):
  model_config = ConfigDict(from_attributes=True)

  id: UUID
  tenant_id: UUID
  product_id: UUID
  from_location_id: UUID | None
  to_location_id: UUID | None
  quantity: Decimal
  unit_cost: Decimal | None
  move_type: str
  reference: str | None
  created_by: UUID | None
  created_at: datetime
