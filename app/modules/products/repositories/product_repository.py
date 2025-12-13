"""Product repository for data access operations."""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.modules.products.models.product import (
    Category,
    Product,
    ProductBarcode,
    ProductVariant,
)


class ProductRepository:
    """Repository for product data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, product_data: dict) -> Product:
        """Create a new product."""
        product = Product(**product_data)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_by_id(self, product_id: UUID, tenant_id: UUID) -> Product | None:
        """Get product by ID and tenant ID."""
        return (
            self.db.query(Product)
            .filter(Product.id == product_id, Product.tenant_id == tenant_id)
            .first()
        )

    def get_by_sku(self, tenant_id: UUID, sku: str) -> Product | None:
        """Get product by SKU and tenant ID."""
        return (
            self.db.query(Product)
            .filter(Product.tenant_id == tenant_id, Product.sku == sku)
            .first()
        )

    def get_all_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        """Get all products by tenant with pagination."""
        return (
            self.db.query(Product)
            .filter(Product.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_by_category(
        self, tenant_id: UUID, category_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        """Get all products by category and tenant with pagination and category eager loaded."""
        return (
            self.db.query(Product)
            .filter(
                Product.tenant_id == tenant_id,
                Product.category_id == category_id,
            )
            .options(joinedload(Product.category))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search(
        self, tenant_id: UUID, query: str, skip: int = 0, limit: int = 100
    ) -> list[Product]:
        """Search products by name or SKU within tenant with category eager loaded."""
        search_pattern = f"%{query}%"
        return (
            self.db.query(Product)
            .filter(
                Product.tenant_id == tenant_id,
                or_(
                    Product.name.ilike(search_pattern),
                    Product.sku.ilike(search_pattern),
                ),
            )
            .options(joinedload(Product.category))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(self, product: Product, product_data: dict) -> Product:
        """Update product data."""
        for key, value in product_data.items():
            if value is not None:
                setattr(product, key, value)
        self.db.commit()
        self.db.refresh(product)
        return product

    def delete(self, product: Product) -> None:
        """Delete a product (hard delete)."""
        self.db.delete(product)
        self.db.commit()

    def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count products by tenant."""
        return self.db.query(Product).filter(Product.tenant_id == tenant_id).count()


class CategoryRepository:
    """Repository for category data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_category(self, category_data: dict) -> Category:
        """Create a new category."""
        category = Category(**category_data)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def get_category_by_id(self, category_id: UUID, tenant_id: UUID) -> Category | None:
        """Get category by ID and tenant ID."""
        return (
            self.db.query(Category)
            .filter(Category.id == category_id, Category.tenant_id == tenant_id)
            .first()
        )

    def get_category_by_slug(self, tenant_id: UUID, slug: str) -> Category | None:
        """Get category by slug and tenant ID."""
        return (
            self.db.query(Category)
            .filter(Category.tenant_id == tenant_id, Category.slug == slug)
            .first()
        )

    def get_all_categories_by_tenant(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[Category]:
        """Get all categories by tenant with pagination."""
        return (
            self.db.query(Category)
            .filter(Category.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_category(self, category: Category, category_data: dict) -> Category:
        """Update category data."""
        for key, value in category_data.items():
            if value is not None:
                setattr(category, key, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_category(self, category: Category) -> None:
        """Delete a category (hard delete)."""
        self.db.delete(category)
        self.db.commit()


class ProductVariantRepository:
    """Repository for product variant data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_variant(self, variant_data: dict) -> ProductVariant:
        """Create a new product variant."""
        variant = ProductVariant(**variant_data)
        self.db.add(variant)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def get_variant_by_id(self, variant_id: UUID) -> ProductVariant | None:
        """Get variant by ID."""
        return (
            self.db.query(ProductVariant)
            .filter(ProductVariant.id == variant_id)
            .first()
        )

    def get_variants_by_product(self, product_id: UUID) -> list[ProductVariant]:
        """Get all variants for a product."""
        return (
            self.db.query(ProductVariant)
            .filter(ProductVariant.product_id == product_id)
            .all()
        )

    def update_variant(
        self, variant: ProductVariant, variant_data: dict
    ) -> ProductVariant:
        """Update variant data."""
        for key, value in variant_data.items():
            if value is not None:
                setattr(variant, key, value)
        self.db.commit()
        self.db.refresh(variant)
        return variant

    def delete_variant(self, variant: ProductVariant) -> None:
        """Delete a variant (hard delete)."""
        self.db.delete(variant)
        self.db.commit()


class ProductBarcodeRepository:
    """Repository for product barcode data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create_barcode(self, barcode_data: dict) -> ProductBarcode:
        """Create a new product barcode."""
        barcode = ProductBarcode(**barcode_data)
        self.db.add(barcode)
        self.db.commit()
        self.db.refresh(barcode)
        return barcode

    def get_barcode_by_id(
        self, barcode_id: UUID, tenant_id: UUID
    ) -> ProductBarcode | None:
        """Get barcode by ID and tenant ID."""
        return (
            self.db.query(ProductBarcode)
            .filter(
                ProductBarcode.id == barcode_id,
                ProductBarcode.tenant_id == tenant_id,
            )
            .first()
        )

    def get_by_barcode(self, tenant_id: UUID, barcode: str) -> ProductBarcode | None:
        """Get barcode by barcode value and tenant ID."""
        return (
            self.db.query(ProductBarcode)
            .filter(
                ProductBarcode.tenant_id == tenant_id,
                ProductBarcode.barcode == barcode,
            )
            .first()
        )

    def get_barcodes_by_product(self, product_id: UUID) -> list[ProductBarcode]:
        """Get all barcodes for a product."""
        return (
            self.db.query(ProductBarcode)
            .filter(ProductBarcode.product_id == product_id)
            .all()
        )

    def get_barcodes_by_variant(self, variant_id: UUID) -> list[ProductBarcode]:
        """Get all barcodes for a variant."""
        return (
            self.db.query(ProductBarcode)
            .filter(ProductBarcode.variant_id == variant_id)
            .all()
        )

    def update_barcode(
        self, barcode: ProductBarcode, barcode_data: dict
    ) -> ProductBarcode:
        """Update barcode data."""
        for key, value in barcode_data.items():
            if value is not None:
                setattr(barcode, key, value)
        self.db.commit()
        self.db.refresh(barcode)
        return barcode

    def delete_barcode(self, barcode: ProductBarcode) -> None:
        """Delete a barcode (hard delete)."""
        self.db.delete(barcode)
        self.db.commit()



