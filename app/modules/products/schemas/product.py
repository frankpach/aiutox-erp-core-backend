"""Product schemas for API requests and responses."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


# Category Schemas
class CategoryBase(BaseModel):
    """Base category schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Category name")
    description: str | None = Field(None, description="Category description")
    slug: str = Field(
        ..., min_length=1, max_length=100, description="Category URL slug"
    )


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    is_active: bool = Field(True, description="Whether the category is active")


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Category name"
    )
    description: str | None = Field(None, description="Category description")
    slug: str | None = Field(
        None, min_length=1, max_length=100, description="Category URL slug"
    )
    is_active: bool | None = Field(None, description="Whether the category is active")


class CategoryResponse(CategoryBase):
    """Schema for category response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Category ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    is_active: bool = Field(..., description="Whether the category is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Product Schemas
class ProductBase(BaseModel):
    """Base product schema with common fields."""

    sku: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Product SKU (Stock Keeping Unit)",
    )
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: str | None = Field(None, description="Product description")
    category_id: UUID | None = Field(None, description="Category ID")
    price: Decimal | None = Field(None, ge=0, description="Product price")
    cost: Decimal | None = Field(None, ge=0, description="Product cost")
    currency: str = Field(
        default="USD", max_length=3, description="Currency code (ISO 4217)"
    )
    weight: Decimal | None = Field(None, ge=0, description="Product weight")
    dimensions: dict[str, Any] | None = Field(
        None, description="Product dimensions (JSON object)"
    )
    unit_of_measure: str | None = Field(
        None, max_length=20, description="Unit of measure"
    )
    track_inventory: bool = Field(
        True, description="Whether to track inventory for this product"
    )
    meta: dict[str, Any] | None = Field(
        None, description="Additional metadata (JSON object)"
    )


class ProductCreate(ProductBase):
    """Schema for creating a new product."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    is_active: bool = Field(True, description="Whether the product is active")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""

    sku: str | None = Field(
        None, min_length=1, max_length=100, description="Product SKU"
    )
    name: str | None = Field(
        None, min_length=1, max_length=255, description="Product name"
    )
    description: str | None = Field(None, description="Product description")
    category_id: UUID | None = Field(None, description="Category ID")
    price: Decimal | None = Field(None, ge=0, description="Product price")
    cost: Decimal | None = Field(None, ge=0, description="Product cost")
    currency: str | None = Field(None, max_length=3, description="Currency code")
    weight: Decimal | None = Field(None, ge=0, description="Product weight")
    dimensions: dict[str, Any] | None = Field(None, description="Product dimensions")
    unit_of_measure: str | None = Field(
        None, max_length=20, description="Unit of measure"
    )
    is_active: bool | None = Field(
        None,
        description="Whether the product is active. Setting to False performs a soft delete.",
    )
    track_inventory: bool | None = Field(None, description="Whether to track inventory")
    meta: dict[str, Any] | None = Field(None, description="Additional metadata")


class ProductResponse(ProductBase):
    """Schema for product response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Product ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    is_active: bool = Field(..., description="Whether the product is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ProductVariant Schemas
class ProductVariantBase(BaseModel):
    """Base product variant schema with common fields."""

    sku: str = Field(..., min_length=1, max_length=100, description="Variant SKU")
    name: str = Field(..., min_length=1, max_length=255, description="Variant name")
    price: Decimal | None = Field(
        None, ge=0, description="Variant-specific price (overrides product price)"
    )
    cost: Decimal | None = Field(
        None, ge=0, description="Variant-specific cost (overrides product cost)"
    )
    attributes: dict[str, Any] | None = Field(
        None, description="Variant attributes (e.g., color, size) as JSON object"
    )
    image_url: str | None = Field(None, max_length=500, description="Variant image URL")
    is_active: bool = Field(True, description="Whether the variant is active")


class ProductVariantCreate(ProductVariantBase):
    """Schema for creating a new product variant."""

    product_id: UUID = Field(..., description="Product ID")


class ProductVariantUpdate(BaseModel):
    """Schema for updating a product variant."""

    sku: str | None = Field(
        None, min_length=1, max_length=100, description="Variant SKU"
    )
    name: str | None = Field(
        None, min_length=1, max_length=255, description="Variant name"
    )
    price: Decimal | None = Field(None, ge=0, description="Variant-specific price")
    cost: Decimal | None = Field(None, ge=0, description="Variant-specific cost")
    attributes: dict[str, Any] | None = Field(None, description="Variant attributes")
    image_url: str | None = Field(None, max_length=500, description="Variant image URL")
    is_active: bool | None = Field(None, description="Whether the variant is active")


class ProductVariantResponse(ProductVariantBase):
    """Schema for product variant response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Variant ID")
    product_id: UUID = Field(..., description="Product ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ProductBarcode Schemas
class ProductBarcodeBase(BaseModel):
    """Base product barcode schema with common fields."""

    barcode: str = Field(..., min_length=1, max_length=128, description="Barcode value")
    barcode_type: str | None = Field(
        None, max_length=20, description="Barcode type (e.g., EAN13, UPC, CODE128)"
    )
    is_primary: bool = Field(False, description="Whether this is the primary barcode")


class ProductBarcodeCreate(ProductBarcodeBase):
    """Schema for creating a new product barcode."""

    tenant_id: UUID = Field(..., description="Tenant ID")
    product_id: UUID | None = Field(
        None, description="Product ID (required if variant_id is not provided)"
    )
    variant_id: UUID | None = Field(
        None, description="Variant ID (required if product_id is not provided)"
    )


class ProductBarcodeUpdate(BaseModel):
    """Schema for updating a product barcode."""

    barcode: str | None = Field(
        None, min_length=1, max_length=128, description="Barcode value"
    )
    barcode_type: str | None = Field(None, max_length=20, description="Barcode type")
    is_primary: bool | None = Field(
        None, description="Whether this is the primary barcode"
    )


class ProductBarcodeResponse(ProductBarcodeBase):
    """Schema for product barcode response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Barcode ID")
    tenant_id: UUID = Field(..., description="Tenant ID")
    product_id: UUID | None = Field(None, description="Product ID")
    variant_id: UUID | None = Field(None, description="Variant ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")










