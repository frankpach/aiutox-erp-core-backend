"""Products module for catalog management."""

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface, ModuleNavigationItem
from app.modules.products.api import router
from app.modules.products.models.product import (
    Category,
    Product,
    ProductBarcode,
    ProductVariant,
)
from app.modules.products.permissions import (
    PRODUCTS_CREATE,
    PRODUCTS_MANAGE,
    PRODUCTS_VIEW,
)


class ProductsModule(ModuleInterface):
    """Products module for catalog management."""

    def __init__(self, db: Session | None = None):
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

    def get_router(self) -> APIRouter | None:
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

    def get_navigation_items(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="products.main",
                label="Productos",
                path="/products",
                permission=PRODUCTS_VIEW,
                icon="grid",
                order=0,
            ),
            ModuleNavigationItem(
                id="products.create",
                label="Nuevo producto",
                path="/products-create",
                permission=PRODUCTS_CREATE,
                icon="grid",
                order=10,
            ),
        ]

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="products.config",
                label="Configuración de catálogo",
                path="/config/modules?module=products",
                permission=PRODUCTS_MANAGE,
                icon="settings",
                category="Configuración",
                order=0,
            )
        ]


# Export module instance factory
def create_module(db: Session | None = None) -> ProductsModule:
    """Create a ProductsModule instance.

    Args:
        db: Optional database session

    Returns:
        ProductsModule instance
    """
    return ProductsModule(db)










