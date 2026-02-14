from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface
from app.modules.inventory.api import router
from app.modules.inventory.models.inventory import Location, StockMove, Warehouse


class InventoryModule(ModuleInterface):
  def __init__(self, db: Session | None = None):
    self._db = db
    self._config_service = ConfigService(db) if db else None

  @property
  def module_id(self) -> str:
    return "inventory"

  @property
  def module_type(self) -> str:
    return "business"

  @property
  def enabled(self) -> bool:
    if self._db and self._config_service:
      try:
        return True
      except Exception:
        pass
    return True

  def get_router(self) -> APIRouter | None:
    return router

  def get_models(self) -> list:
    return [Warehouse, Location, StockMove]

  def get_dependencies(self) -> list[str]:
    return ["auth", "users", "products", "pubsub"]

  @property
  def module_name(self) -> str:
    return "Inventory"

  @property
  def description(self) -> str:
    return "Módulo empresarial: almacenes, ubicaciones y movimientos de stock."


def create_module(db: Session | None = None) -> InventoryModule:
  return InventoryModule(db)
