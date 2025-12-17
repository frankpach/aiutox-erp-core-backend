"""Product service for business logic."""

import logging
import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import create_audit_log_entry
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.modules.products.models.product import Product
from app.modules.products.repositories.product_repository import (
    CategoryRepository,
    ProductBarcodeRepository,
    ProductRepository,
    ProductVariantRepository,
)
from app.modules.products.schemas.product import (
    CategoryCreate,
    CategoryUpdate,
    ProductBarcodeCreate,
    ProductBarcodeUpdate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantUpdate,
)

logger = logging.getLogger(__name__)

# Validation patterns
SKU_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,100}$")
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
VALID_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "BRL",
    "MXN", "RUB", "ZAR", "KRW", "SGD", "HKD", "NZD", "SEK", "NOK", "DKK",
    "PLN", "CZK", "HUF", "TRY", "ILS", "CLP", "ARS", "COP", "PEN", "UYU",
}
EAN13_PATTERN = re.compile(r"^\d{13}$")
UPC_PATTERN = re.compile(r"^\d{12}$")
CODE128_PATTERN = re.compile(r"^[\x20-\x7E]{1,128}$")  # ASCII printable characters


class ProductService:
    """Service for product business logic."""

    def __init__(self, db: Session, event_publisher: EventPublisher | None = None):
        """Initialize service with database session.

        Args:
            db: Database session
            event_publisher: EventPublisher instance (optional, will be created if not provided)
        """
        self.db = db
        self.product_repo = ProductRepository(db)
        self.category_repo = CategoryRepository(db)
        self.variant_repo = ProductVariantRepository(db)
        self.barcode_repo = ProductBarcodeRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()

    # Validation methods
    @staticmethod
    def _validate_sku(sku: str) -> None:
        """Validate SKU format.

        Args:
            sku: SKU to validate.

        Raises:
            ValueError: If SKU format is invalid.
        """
        if not SKU_PATTERN.match(sku):
            raise ValueError(
                "SKU must be alphanumeric with dashes/underscores, 3-100 characters"
            )

    @staticmethod
    def _validate_currency(currency: str) -> None:
        """Validate currency code (ISO 4217).

        Args:
            currency: Currency code to validate.

        Raises:
            ValueError: If currency format is invalid or not supported.
        """
        if not CURRENCY_PATTERN.match(currency):
            raise ValueError("Currency must be a valid ISO 4217 code (e.g., USD, EUR)")
        if currency not in VALID_CURRENCIES:
            raise ValueError(f"Currency '{currency}' is not supported")

    @staticmethod
    def _validate_barcode(barcode: str, barcode_type: Optional[str] = None) -> None:
        """Validate barcode format based on type.

        Args:
            barcode: Barcode value to validate.
            barcode_type: Type of barcode (EAN13, UPC, CODE128).

        Raises:
            ValueError: If barcode format is invalid.
        """
        if barcode_type == "EAN13":
            if not EAN13_PATTERN.match(barcode):
                raise ValueError("EAN13 barcode must be exactly 13 digits")
        elif barcode_type == "UPC":
            if not UPC_PATTERN.match(barcode):
                raise ValueError("UPC barcode must be exactly 12 digits")
        elif barcode_type == "CODE128":
            if not CODE128_PATTERN.match(barcode):
                raise ValueError(
                    "CODE128 barcode must be 1-128 ASCII printable characters"
                )
        # If no type specified, only validate basic length
        elif len(barcode) < 1 or len(barcode) > 128:
            raise ValueError("Barcode must be 1-128 characters")

    # Product methods
    def create_product(
        self,
        product_data: ProductCreate,
        tenant_id: UUID,
        created_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Create a new product with business logic validation.

        Validates SKU uniqueness, format, currency, and category existence.
        Creates audit log entry if created_by is provided.

        Args:
            product_data: Product creation data.
            tenant_id: Tenant ID for multi-tenancy.
            created_by: UUID of user who created this product (None for system).
            ip_address: Client IP address (optional, for audit).
            user_agent: Client user agent (optional, for audit).

        Returns:
            dict: Product data with serialized Decimal fields.

        Raises:
            ValueError: If SKU format is invalid, currency is not supported,
                       SKU already exists, or category not found.

        Example:
            >>> service = ProductService(db)
            >>> product_data = ProductCreate(
            ...     tenant_id=tenant_id,
            ...     sku="PROD-001",
            ...     name="Test Product",
            ...     price=Decimal("10.00"),
            ...     currency="USD"
            ... )
            >>> result = service.create_product(product_data, tenant_id)
            >>> assert result["sku"] == "PROD-001"
        """
        # Validate SKU format
        self._validate_sku(product_data.sku)

        # Validate currency if provided
        if product_data.currency:
            self._validate_currency(product_data.currency)

        # Check if product with same SKU already exists
        existing_product = self.product_repo.get_by_sku(tenant_id, product_data.sku)
        if existing_product:
            raise ValueError(f"Product with SKU '{product_data.sku}' already exists")

        # Validate category if provided
        if product_data.category_id:
            category = self.category_repo.get_category_by_id(
                product_data.category_id, tenant_id
            )
            if not category:
                raise ValueError(
                    f"Category with ID '{product_data.category_id}' not found"
                )

        # Create product
        product_dict = product_data.model_dump()
        product = self.product_repo.create(product_dict)

        # Log product creation
        if created_by:
            create_audit_log_entry(
                db=self.db,
                user_id=created_by,
                tenant_id=tenant_id,
                action="create_product",
                resource_type="product",
                resource_id=product.id,
                details={"sku": product.sku, "name": product.name},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        # Publish event (fire and forget)
        try:
            # Note: This is a synchronous method, so we can't await.
            # The event publisher will handle async execution internally.
            # For now, we'll log that the event should be published.
            # In a production environment, you might want to use a background task queue.
            logger.info(
                f"Product created: {product.id}, event should be published via background task"
            )
            # TODO: Implement proper async event publishing via background task
        except Exception as e:
            logger.error(f"Failed to prepare product.created event: {e}")
            # Don't fail the operation if event publishing fails

        return self._product_to_dict(product)

    def get_product(self, product_id: UUID, tenant_id: UUID) -> dict | None:
        """Get product by ID."""
        product = self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            return None
        return self._product_to_dict(product)

    def list_products(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        category_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        """
        List products by tenant with pagination and filters.

        Args:
            tenant_id: Tenant UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            category_id: Optional category filter.
            search: Optional search query (searches name and SKU).

        Returns:
            Tuple of (list of product dicts, total count).
        """
        if search:
            products = self.product_repo.search(
                tenant_id, search, skip=skip, limit=limit
            )
            total = len(products)  # Simplified count for search
        elif category_id:
            products = self.product_repo.get_all_by_category(
                tenant_id, category_id, skip=skip, limit=limit
            )
            total = len(products)  # Simplified count for category filter
        else:
            products = self.product_repo.get_all_by_tenant(
                tenant_id, skip=skip, limit=limit
            )
            total = self.product_repo.count_by_tenant(tenant_id)

        product_dicts = [self._product_to_dict(product) for product in products]
        return product_dicts, total

    def update_product(
        self,
        product_id: UUID,
        product_data: ProductUpdate,
        tenant_id: UUID,
        updated_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict | None:
        """
        Update product with business logic validation.

        Validates SKU format, currency, and category existence if being updated.
        Tracks changes for audit log.

        Args:
            product_id: Product ID to update.
            product_data: Product update data.
            tenant_id: Tenant ID for multi-tenancy.
            updated_by: UUID of user who updated this product (None for system).
            ip_address: Client IP address (optional, for audit).
            user_agent: Client user agent (optional, for audit).

        Returns:
            dict | None: Updated product data, or None if product not found.

        Raises:
            ValueError: If SKU format is invalid, currency is not supported,
                       SKU already exists, or category not found.
        """
        product = self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            return None

        # Track changes for audit log
        changes = {}

        # Check SKU uniqueness if SKU is being updated
        if product_data.sku and product_data.sku != product.sku:
            # Validate SKU format
            self._validate_sku(product_data.sku)
            existing_product = self.product_repo.get_by_sku(tenant_id, product_data.sku)
            if existing_product:
                raise ValueError(
                    f"Product with SKU '{product_data.sku}' already exists"
                )
            changes["sku"] = {"old": product.sku, "new": product_data.sku}

        # Validate currency if provided
        if product_data.currency:
            self._validate_currency(product_data.currency)

        # Validate category if provided
        if product_data.category_id and product_data.category_id != product.category_id:
            category = self.category_repo.get_category_by_id(
                product_data.category_id, tenant_id
            )
            if not category:
                raise ValueError(
                    f"Category with ID '{product_data.category_id}' not found"
                )
            changes["category_id"] = {
                "old": str(product.category_id) if product.category_id else None,
                "new": str(product_data.category_id),
            }

        # Track other important changes
        update_data = product_data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != product.name:
            changes["name"] = {"old": product.name, "new": update_data["name"]}
        if "is_active" in update_data and update_data["is_active"] != product.is_active:
            changes["is_active"] = {
                "old": product.is_active,
                "new": update_data["is_active"],
            }

        # Update product
        updated_product = self.product_repo.update(product, update_data)

        # Log product update (only if there are significant changes)
        if updated_by and changes:
            create_audit_log_entry(
                db=self.db,
                user_id=updated_by,
                tenant_id=tenant_id,
                action="update_product",
                resource_type="product",
                resource_id=product_id,
                details={"changes": changes},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        # Publish event (fire and forget)
        try:
            logger.info(
                f"Product updated: {product_id}, event should be published via background task"
            )
            # TODO: Implement proper async event publishing via background task
        except Exception as e:
            logger.error(f"Failed to prepare product.updated event: {e}")
            # Don't fail the operation if event publishing fails

        return self._product_to_dict(updated_product)

    def delete_product(
        self,
        product_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Soft delete product (set is_active=False).

        Args:
            product_id: Product ID to delete.
            tenant_id: Tenant ID.
            deleted_by: UUID of user who deleted this product (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        product = self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            return False

        product.is_active = False
        self.product_repo.update(product, {})

        # Log product deletion
        if deleted_by:
            create_audit_log_entry(
                db=self.db,
                user_id=deleted_by,
                tenant_id=tenant_id,
                action="delete_product",
                resource_type="product",
                resource_id=product_id,
                details={"sku": product.sku, "name": product.name},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        # Publish event (fire and forget)
        try:
            logger.info(
                f"Product deleted: {product_id}, event should be published via background task"
            )
            # TODO: Implement proper async event publishing via background task
        except Exception as e:
            logger.error(f"Failed to prepare product.deleted event: {e}")
            # Don't fail the operation if event publishing fails

        return True

    # Category methods
    def create_category(
        self,
        category_data: CategoryCreate,
        tenant_id: UUID,
        created_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Create a new category with business logic validation.

        Args:
            category_data: Category creation data.
            tenant_id: Tenant ID.
            created_by: UUID of user who created this category (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        # Check if category with same name or slug already exists
        existing_by_name = self.category_repo.get_category_by_slug(
            tenant_id, category_data.slug
        )
        if existing_by_name:
            raise ValueError(
                f"Category with slug '{category_data.slug}' already exists"
            )

        # Create category
        category_dict = category_data.model_dump()
        category = self.category_repo.create_category(category_dict)

        # Log category creation
        if created_by:
            create_audit_log_entry(
                db=self.db,
                user_id=created_by,
                tenant_id=tenant_id,
                action="create_category",
                resource_type="category",
                resource_id=category.id,
                details={"name": category.name, "slug": category.slug},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._category_to_dict(category)

    def list_categories(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[dict], int]:
        """
        List categories by tenant with pagination.

        Args:
            tenant_id: Tenant UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (list of category dicts, total count).
        """
        categories = self.category_repo.get_all_categories_by_tenant(
            tenant_id, skip=skip, limit=limit
        )
        # Simplified count - in production, use a count query
        total = len(categories)
        category_dicts = [self._category_to_dict(category) for category in categories]
        return category_dicts, total

    def update_category(
        self,
        category_id: UUID,
        category_data: CategoryUpdate,
        tenant_id: UUID,
        updated_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict | None:
        """
        Update category with business logic validation.

        Args:
            category_id: Category ID to update.
            category_data: Category update data.
            tenant_id: Tenant ID.
            updated_by: UUID of user who updated this category (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        category = self.category_repo.get_category_by_id(category_id, tenant_id)
        if not category:
            return None

        # Check slug uniqueness if slug is being updated
        if category_data.slug and category_data.slug != category.slug:
            existing_category = self.category_repo.get_category_by_slug(
                tenant_id, category_data.slug
            )
            if existing_category:
                raise ValueError(
                    f"Category with slug '{category_data.slug}' already exists"
                )

        # Update category
        update_data = category_data.model_dump(exclude_unset=True)
        updated_category = self.category_repo.update_category(category, update_data)

        # Log category update
        if updated_by:
            create_audit_log_entry(
                db=self.db,
                user_id=updated_by,
                tenant_id=tenant_id,
                action="update_category",
                resource_type="category",
                resource_id=category_id,
                details={"name": updated_category.name},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._category_to_dict(updated_category)

    def delete_category(
        self,
        category_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Delete category (hard delete).

        Args:
            category_id: Category ID to delete.
            tenant_id: Tenant ID.
            deleted_by: UUID of user who deleted this category (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        category = self.category_repo.get_category_by_id(category_id, tenant_id)
        if not category:
            return False

        self.category_repo.delete_category(category)

        # Log category deletion
        if deleted_by:
            create_audit_log_entry(
                db=self.db,
                user_id=deleted_by,
                tenant_id=tenant_id,
                action="delete_category",
                resource_type="category",
                resource_id=category_id,
                details={"name": category.name},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return True

    # Variant methods
    def create_variant(
        self,
        product_id: UUID,
        variant_data: ProductVariantCreate,
        tenant_id: UUID,
        created_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Create a new product variant with business logic validation.

        Args:
            product_id: Product ID.
            variant_data: Variant creation data.
            tenant_id: Tenant ID.
            created_by: UUID of user who created this variant (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        # Verify product exists and belongs to tenant
        product = self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            raise ValueError(f"Product with ID '{product_id}' not found")

        # Validate SKU format
        self._validate_sku(variant_data.sku)

        # Check if variant with same SKU already exists for this product
        existing_variants = self.variant_repo.get_variants_by_product(product_id)
        for variant in existing_variants:
            if variant.sku == variant_data.sku:
                raise ValueError(
                    f"Variant with SKU '{variant_data.sku}' already exists for this product"
                )

        # Create variant
        variant_dict = variant_data.model_dump()
        variant = self.variant_repo.create_variant(variant_dict)

        # Log variant creation
        if created_by:
            create_audit_log_entry(
                db=self.db,
                user_id=created_by,
                tenant_id=tenant_id,
                action="create_product_variant",
                resource_type="product_variant",
                resource_id=variant.id,
                details={
                    "product_id": str(product_id),
                    "sku": variant.sku,
                    "name": variant.name,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._variant_to_dict(variant)

    def list_variants(self, product_id: UUID, tenant_id: UUID) -> list[dict]:
        """
        List variants for a product.

        Args:
            product_id: Product UUID.
            tenant_id: Tenant UUID.

        Returns:
            List of variant dicts.
        """
        # Verify product exists and belongs to tenant
        product = self.product_repo.get_by_id(product_id, tenant_id)
        if not product:
            return []

        variants = self.variant_repo.get_variants_by_product(product_id)
        return [self._variant_to_dict(variant) for variant in variants]

    def update_variant(
        self,
        variant_id: UUID,
        variant_data: ProductVariantUpdate,
        tenant_id: UUID,
        updated_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict | None:
        """
        Update variant with business logic validation.

        Args:
            variant_id: Variant ID to update.
            variant_data: Variant update data.
            tenant_id: Tenant ID.
            updated_by: UUID of user who updated this variant (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        variant = self.variant_repo.get_variant_by_id(variant_id)
        if not variant:
            return None

        # Verify product belongs to tenant
        product = self.product_repo.get_by_id(variant.product_id, tenant_id)
        if not product:
            return None

        # Check SKU uniqueness if SKU is being updated
        if variant_data.sku and variant_data.sku != variant.sku:
            # Validate SKU format
            self._validate_sku(variant_data.sku)
            existing_variants = self.variant_repo.get_variants_by_product(
                variant.product_id
            )
            for existing_variant in existing_variants:
                if (
                    existing_variant.sku == variant_data.sku
                    and existing_variant.id != variant_id
                ):
                    raise ValueError(
                        f"Variant with SKU '{variant_data.sku}' already exists for this product"
                    )

        # Update variant
        update_data = variant_data.model_dump(exclude_unset=True)
        updated_variant = self.variant_repo.update_variant(variant, update_data)

        # Log variant update
        if updated_by:
            create_audit_log_entry(
                db=self.db,
                user_id=updated_by,
                tenant_id=tenant_id,
                action="update_product_variant",
                resource_type="product_variant",
                resource_id=variant_id,
                details={"sku": updated_variant.sku},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._variant_to_dict(updated_variant)

    def delete_variant(
        self,
        variant_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Delete variant (hard delete).

        Args:
            variant_id: Variant ID to delete.
            tenant_id: Tenant ID.
            deleted_by: UUID of user who deleted this variant (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        variant = self.variant_repo.get_variant_by_id(variant_id)
        if not variant:
            return False

        # Verify product belongs to tenant
        product = self.product_repo.get_by_id(variant.product_id, tenant_id)
        if not product:
            return False

        self.variant_repo.delete_variant(variant)

        # Log variant deletion
        if deleted_by:
            create_audit_log_entry(
                db=self.db,
                user_id=deleted_by,
                tenant_id=tenant_id,
                action="delete_product_variant",
                resource_type="product_variant",
                resource_id=variant_id,
                details={"sku": variant.sku},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return True

    # Barcode methods
    def create_barcode(
        self,
        product_id: UUID | None,
        variant_id: UUID | None,
        barcode_data: ProductBarcodeCreate,
        tenant_id: UUID,
        created_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Create a new product barcode with business logic validation.

        Args:
            product_id: Product ID (optional if variant_id is provided).
            variant_id: Variant ID (optional if product_id is provided).
            barcode_data: Barcode creation data.
            tenant_id: Tenant ID.
            created_by: UUID of user who created this barcode (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        # Validate that either product_id or variant_id is provided
        if not product_id and not variant_id:
            raise ValueError("Either product_id or variant_id must be provided")

        # Verify product or variant exists and belongs to tenant
        if product_id:
            product = self.product_repo.get_by_id(product_id, tenant_id)
            if not product:
                raise ValueError(f"Product with ID '{product_id}' not found")
        if variant_id:
            variant = self.variant_repo.get_variant_by_id(variant_id)
            if not variant:
                raise ValueError(f"Variant with ID '{variant_id}' not found")
            # Verify variant's product belongs to tenant
            product = self.product_repo.get_by_id(variant.product_id, tenant_id)
            if not product:
                raise ValueError("Variant's product does not belong to tenant")

        # Validate barcode format
        self._validate_barcode(barcode_data.barcode, barcode_data.barcode_type)

        # Check if barcode already exists
        existing_barcode = self.barcode_repo.get_by_barcode(
            tenant_id, barcode_data.barcode
        )
        if existing_barcode:
            raise ValueError(f"Barcode '{barcode_data.barcode}' already exists")

        # Create barcode
        barcode_dict = barcode_data.model_dump()
        if product_id:
            barcode_dict["product_id"] = product_id
        if variant_id:
            barcode_dict["variant_id"] = variant_id
        barcode = self.barcode_repo.create_barcode(barcode_dict)

        # Log barcode creation
        if created_by:
            create_audit_log_entry(
                db=self.db,
                user_id=created_by,
                tenant_id=tenant_id,
                action="create_product_barcode",
                resource_type="product_barcode",
                resource_id=barcode.id,
                details={
                    "barcode": barcode.barcode,
                    "product_id": str(product_id) if product_id else None,
                    "variant_id": str(variant_id) if variant_id else None,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._barcode_to_dict(barcode)

    def get_by_barcode(self, tenant_id: UUID, barcode: str) -> dict | None:
        """
        Get product or variant by barcode.

        Args:
            tenant_id: Tenant UUID.
            barcode: Barcode value.

        Returns:
            Dict with product or variant information, or None if not found.
        """
        barcode_obj = self.barcode_repo.get_by_barcode(tenant_id, barcode)
        if not barcode_obj:
            return None

        result = self._barcode_to_dict(barcode_obj)
        # Include product or variant information
        if barcode_obj.product_id:
            product = self.product_repo.get_by_id(barcode_obj.product_id, tenant_id)
            if product:
                result["product"] = self._product_to_dict(product)
        if barcode_obj.variant_id:
            variant = self.variant_repo.get_variant_by_id(barcode_obj.variant_id)
            if variant:
                result["variant"] = self._variant_to_dict(variant)
                # Also include product info
                product = self.product_repo.get_by_id(variant.product_id, tenant_id)
                if product:
                    result["product"] = self._product_to_dict(product)

        return result

    def list_barcodes(
        self,
        product_id: UUID | None,
        variant_id: UUID | None,
        tenant_id: UUID,
    ) -> list[dict]:
        """
        List barcodes for a product or variant.

        Args:
            product_id: Product UUID (optional if variant_id is provided).
            variant_id: Variant UUID (optional if product_id is provided).
            tenant_id: Tenant UUID.

        Returns:
            List of barcode dicts.
        """
        if variant_id:
            barcodes = self.barcode_repo.get_barcodes_by_variant(variant_id)
        elif product_id:
            barcodes = self.barcode_repo.get_barcodes_by_product(product_id)
        else:
            return []

        return [self._barcode_to_dict(barcode) for barcode in barcodes]

    def update_barcode(
        self,
        barcode_id: UUID,
        barcode_data: ProductBarcodeUpdate,
        tenant_id: UUID,
        updated_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict | None:
        """
        Update barcode with business logic validation.

        Args:
            barcode_id: Barcode ID to update.
            barcode_data: Barcode update data.
            tenant_id: Tenant ID.
            updated_by: UUID of user who updated this barcode (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        barcode = self.barcode_repo.get_barcode_by_id(barcode_id, tenant_id)
        if not barcode:
            return None

        # Check barcode uniqueness if barcode is being updated
        if barcode_data.barcode and barcode_data.barcode != barcode.barcode:
            # Validate barcode format
            self._validate_barcode(
                barcode_data.barcode,
                barcode_data.barcode_type or barcode.barcode_type,
            )
            existing_barcode = self.barcode_repo.get_by_barcode(
                tenant_id, barcode_data.barcode
            )
            if existing_barcode:
                raise ValueError(f"Barcode '{barcode_data.barcode}' already exists")

        # Update barcode
        update_data = barcode_data.model_dump(exclude_unset=True)
        updated_barcode = self.barcode_repo.update_barcode(barcode, update_data)

        # Log barcode update
        if updated_by:
            create_audit_log_entry(
                db=self.db,
                user_id=updated_by,
                tenant_id=tenant_id,
                action="update_product_barcode",
                resource_type="product_barcode",
                resource_id=barcode_id,
                details={"barcode": updated_barcode.barcode},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._barcode_to_dict(updated_barcode)

    def delete_barcode(
        self,
        barcode_id: UUID,
        tenant_id: UUID,
        deleted_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Delete barcode (hard delete).

        Args:
            barcode_id: Barcode ID to delete.
            tenant_id: Tenant ID.
            deleted_by: UUID of user who deleted this barcode (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        barcode = self.barcode_repo.get_barcode_by_id(barcode_id, tenant_id)
        if not barcode:
            return False

        self.barcode_repo.delete_barcode(barcode)

        # Log barcode deletion
        if deleted_by:
            create_audit_log_entry(
                db=self.db,
                user_id=deleted_by,
                tenant_id=tenant_id,
                action="delete_product_barcode",
                resource_type="product_barcode",
                resource_id=barcode_id,
                details={"barcode": barcode.barcode},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return True

    # Helper methods to convert models to dicts
    def _product_to_dict(self, product: Product) -> dict:
        """Convert Product model to dict."""
        return {
            "id": product.id,
            "tenant_id": product.tenant_id,
            "category_id": product.category_id,
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "price": f"{product.price:.2f}" if product.price else None,
            "cost": f"{product.cost:.2f}" if product.cost else None,
            "currency": product.currency,
            "weight": f"{product.weight:.2f}" if product.weight else None,
            "dimensions": product.dimensions,
            "unit_of_measure": product.unit_of_measure,
            "is_active": product.is_active,
            "track_inventory": product.track_inventory,
            "meta": product.meta,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
        }

    def _category_to_dict(self, category) -> dict:
        """Convert Category model to dict."""
        return {
            "id": category.id,
            "tenant_id": category.tenant_id,
            "name": category.name,
            "description": category.description,
            "slug": category.slug,
            "is_active": category.is_active,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }

    def _variant_to_dict(self, variant) -> dict:
        """Convert ProductVariant model to dict."""
        return {
            "id": variant.id,
            "product_id": variant.product_id,
            "sku": variant.sku,
            "name": variant.name,
            "price": f"{variant.price:.2f}" if variant.price else None,
            "cost": f"{variant.cost:.2f}" if variant.cost else None,
            "attributes": variant.attributes,
            "image_url": variant.image_url,
            "is_active": variant.is_active,
            "created_at": variant.created_at,
            "updated_at": variant.updated_at,
        }

    def _barcode_to_dict(self, barcode) -> dict:
        """Convert ProductBarcode model to dict."""
        return {
            "id": barcode.id,
            "tenant_id": barcode.tenant_id,
            "product_id": barcode.product_id,
            "variant_id": barcode.variant_id,
            "barcode": barcode.barcode,
            "barcode_type": barcode.barcode_type,
            "is_primary": barcode.is_primary,
            "created_at": barcode.created_at,
            "updated_at": barcode.updated_at,
        }









