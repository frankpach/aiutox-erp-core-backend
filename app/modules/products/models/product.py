"""Product models for catalog management."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.core.db.session import Base


class Category(Base):
    """Category model for product categorization."""

    __tablename__ = "categories"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    products = relationship("Product", back_populates="category")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_categories_tenant_name"),
        UniqueConstraint("tenant_id", "slug", name="uq_categories_tenant_slug"),
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, tenant_id={self.tenant_id})>"


class Product(Base):
    """Product model for catalog management."""

    __tablename__ = "products"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sku = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Precio y costo (información del producto)
    price = Column(Numeric(10, 2), nullable=True)
    cost = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)

    # Atributos físicos
    weight = Column(Numeric(10, 2), nullable=True)
    dimensions = Column(JSONB, nullable=True)
    unit_of_measure = Column(String(20), nullable=True)

    # Estado y configuración
    is_active = Column(Boolean, default=True, nullable=False)
    track_inventory = Column(Boolean, default=True, nullable=False)
    meta = Column(JSONB, nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    category = relationship("Category", back_populates="products")
    variants = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )
    barcodes = relationship(
        "ProductBarcode", back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
        Index("idx_products_tenant_name", "tenant_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku={self.sku}, name={self.name}, tenant_id={self.tenant_id})>"


class ProductVariant(Base):
    """ProductVariant model for product variations (size, color, etc.)."""

    __tablename__ = "product_variants"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Precios específicos (sobrescriben precio base)
    price = Column(Numeric(10, 2), nullable=True)
    cost = Column(Numeric(10, 2), nullable=True)

    # Atributos
    attributes = Column(JSONB, nullable=True)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    product = relationship("Product", back_populates="variants")
    barcodes = relationship(
        "ProductBarcode", back_populates="variant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("product_id", "sku", name="uq_product_variants_product_sku"),
    )

    def __repr__(self) -> str:
        return f"<ProductVariant(id={self.id}, sku={self.sku}, name={self.name}, product_id={self.product_id})>"


class ProductBarcode(Base):
    """ProductBarcode model for barcode management (supports multiple barcodes per product/variant)."""

    __tablename__ = "product_barcodes"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Referencia al producto (puede ser producto o variante)
    product_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    variant_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Código de barras
    barcode = Column(String(128), nullable=False, unique=True, index=True)
    barcode_type = Column(String(20), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    product = relationship("Product", back_populates="barcodes")
    variant = relationship("ProductVariant", back_populates="barcodes")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "barcode", name="uq_product_barcodes_tenant_barcode"
        ),
        CheckConstraint(
            "(product_id IS NOT NULL) OR (variant_id IS NOT NULL)",
            name="ck_barcode_reference",
        ),
        Index("idx_product_barcodes_barcode", "barcode"),
    )

    def __repr__(self) -> str:
        return f"<ProductBarcode(id={self.id}, barcode={self.barcode}, product_id={self.product_id}, variant_id={self.variant_id})>"



