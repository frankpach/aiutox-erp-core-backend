"""Products data source for reporting."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.reporting.data_source import BaseDataSource
from app.modules.products.repositories.product_repository import ProductRepository


class ProductsDataSource(BaseDataSource):
    """Data source for products reporting."""

    def __init__(self, db: Session, tenant_id: UUID):
        """Initialize products data source.

        Args:
            db: Database session
            tenant_id: Tenant ID
        """
        super().__init__(db, tenant_id)
        self.product_repo = ProductRepository(db)

    async def get_data(
        self, filters: dict[str, Any] | None = None, pagination: dict[str, int] | None = None
    ) -> dict[str, Any]:
        """Get products data.

        Args:
            filters: Filter configuration
            pagination: Pagination configuration

        Returns:
            Dictionary with 'data' and 'total'
        """
        skip = pagination.get("skip", 0) if pagination else 0
        limit = pagination.get("limit", 100) if pagination else 100

        # Apply filters
        category_id = filters.get("category_id") if filters else None
        search = filters.get("search") if filters else None

        # Get products based on filters
        if category_id:
            products = self.product_repo.get_all_by_category(
                tenant_id=self.tenant_id, category_id=category_id, skip=skip, limit=limit
            )
        elif search:
            products = self.product_repo.search(
                tenant_id=self.tenant_id, query=search, skip=skip, limit=limit
            )
        else:
            products = self.product_repo.get_all_by_tenant(
                tenant_id=self.tenant_id, skip=skip, limit=limit
            )

        # Get total count
        total = self.product_repo.count_by_tenant(self.tenant_id)

        # Convert to dictionaries
        data = [
            {
                "id": str(product.id),
                "sku": product.sku,
                "name": product.name,
                "price": float(product.price) if product.price else None,
                "cost": float(product.cost) if product.cost else None,
                "is_active": product.is_active,
            }
            for product in products
        ]

        return {"data": data, "total": total}

    def get_columns(self) -> list[dict[str, Any]]:
        """Get available columns for products.

        Returns:
            List of column definitions
        """
        return [
            {"name": "id", "type": "uuid", "label": "ID"},
            {"name": "sku", "type": "string", "label": "SKU"},
            {"name": "name", "type": "string", "label": "Name"},
            {"name": "price", "type": "decimal", "label": "Price"},
            {"name": "cost", "type": "decimal", "label": "Cost"},
            {"name": "is_active", "type": "boolean", "label": "Active"},
        ]

    def get_filters(self) -> list[dict[str, Any]]:
        """Get available filters for products.

        Returns:
            List of filter definitions
        """
        return [
            {
                "name": "category_id",
                "type": "uuid",
                "label": "Category",
                "options": None,  # Could be populated with actual categories
            },
            {
                "name": "search",
                "type": "string",
                "label": "Search",
                "options": None,
            },
            {
                "name": "is_active",
                "type": "boolean",
                "label": "Active",
                "options": None,
            },
        ]

