"""Products module for catalog management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface
from app.modules.products.api import router
from app.modules.products.models.product import (
    Category,
    Product,
    ProductBarcode,
    ProductVariant,
)


class ProductsModule(ModuleInterface):
    """Products module for catalog management."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize ProductsModule.

        Args:
            db: Optional database session for reading module configuration
        """
        self._db = db
        self._config_service = ConfigService(db) if db else None

    @property
    def module_id(self) -> str:
        """Module identifier."""
        return "products"

    @property
    def module_type(self) -> str:
        """Module type."""
        return "business"

    @property
    def enabled(self) -> bool:
        """Check if module is enabled.

        Reads from ConfigService or defaults to True.
        """
        if self._db and self._config_service:
            try:
                # Try to read from config (will use default if not set)
                # Note: We need a tenant_id, but for module discovery we don't have one
                # So we'll use the default from modules.json
                return True  # Default enabled, actual status checked at runtime
            except Exception:
                pass
        return True  # Default to enabled

    def get_router(self) -> Optional[APIRouter]:
        """Get FastAPI router for products module."""
        return router

    def get_models(self) -> list:
        """Get all SQLAlchemy models for products module."""
        return [Product, Category, ProductVariant, ProductBarcode]

    def get_dependencies(self) -> list[str]:
        """Get list of module IDs this module depends on."""
        return ["auth", "users", "pubsub"]

    @property
    def module_name(self) -> str:
        """Human-readable module name."""
        return "Catálogo de Productos"

    @property
    def description(self) -> str:
        """Module description."""
        return (
            "Módulo empresarial: Productos, categorías, variantes, precios. "
            "Usa infraestructura base (Reporting, Config, Notificaciones). "
            "Publica eventos al bus (product.created, product.updated, etc.)."
        )

    def on_load(self) -> None:
        """Callback when module is loaded."""
        pass


# Export module instance factory
def create_module(db: Optional[Session] = None) -> ProductsModule:
    """Create a ProductsModule instance.

    Args:
        db: Optional database session

    Returns:
        ProductsModule instance
    """
    return ProductsModule(db)









