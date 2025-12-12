"""Unit tests for ProductService using mocks."""

from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.modules.products.services.product_service import ProductService
from app.modules.products.schemas.product import (
    CategoryCreate,
    ProductBarcodeCreate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
)


class TestProductService:
    """Test suite for ProductService unit tests."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_product_repo(self):
        """Mock ProductRepository."""
        with patch("app.modules.products.services.product_service.ProductRepository") as mock:
            repo = Mock()
            mock.return_value = repo
            yield repo

    @pytest.fixture
    def mock_category_repo(self):
        """Mock CategoryRepository."""
        with patch("app.modules.products.services.product_service.CategoryRepository") as mock:
            repo = Mock()
            mock.return_value = repo
            yield repo

    @pytest.fixture
    def mock_variant_repo(self):
        """Mock ProductVariantRepository."""
        with patch("app.modules.products.services.product_service.ProductVariantRepository") as mock:
            repo = Mock()
            mock.return_value = repo
            yield repo

    @pytest.fixture
    def mock_barcode_repo(self):
        """Mock ProductBarcodeRepository."""
        with patch("app.modules.products.services.product_service.ProductBarcodeRepository") as mock:
            repo = Mock()
            mock.return_value = repo
            yield repo

    @pytest.fixture
    def service(
        self, mock_db, mock_product_repo, mock_category_repo, mock_variant_repo, mock_barcode_repo
    ):
        """Create ProductService instance with mocked dependencies."""
        return ProductService(mock_db)

    # Product tests
    def test_create_product_success(self, service, mock_product_repo, mock_category_repo):
        """Test successful product creation."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        product_data = ProductCreate(
            tenant_id=tenant_id,
            sku="TEST-001",
            name="Test Product",
            price=Decimal("10.00"),
            currency="USD",
        )
        mock_product_repo.get_by_sku.return_value = None
        mock_product = Mock()
        mock_product.id = product_id
        mock_product.sku = "TEST-001"
        mock_product.name = "Test Product"
        mock_product.price = Decimal("10.00")
        mock_product.cost = None
        mock_product.weight = None
        mock_product.category_id = None
        mock_product.currency = "USD"
        mock_product.dimensions = None
        mock_product.unit_of_measure = None
        mock_product.track_inventory = True
        mock_product.meta = None
        mock_product.is_active = True
        mock_product.created_at = None
        mock_product.updated_at = None
        mock_product_repo.create.return_value = mock_product

        # Act
        result = service.create_product(product_data, tenant_id)

        # Assert
        assert result["sku"] == "TEST-001"
        assert result["name"] == "Test Product"
        mock_product_repo.get_by_sku.assert_called_once_with(tenant_id, "TEST-001")
        mock_product_repo.create.assert_called_once()

    def test_create_product_duplicate_sku(self, service, mock_product_repo):
        """Test product creation fails with duplicate SKU."""
        # Arrange
        tenant_id = uuid4()
        product_data = ProductCreate(
            tenant_id=tenant_id, sku="TEST-001", name="Test", currency="USD"
        )
        mock_product_repo.get_by_sku.return_value = Mock(sku="TEST-001")

        # Act & Assert
        with pytest.raises(ValueError, match="already exists"):
            service.create_product(product_data, tenant_id)

    def test_create_product_invalid_sku_format(self, service, mock_product_repo):
        """Test product creation fails with invalid SKU format."""
        # Arrange
        tenant_id = uuid4()
        product_data = ProductCreate(
            tenant_id=tenant_id, sku="SKU WITH SPACES", name="Test", currency="USD"
        )
        mock_product_repo.get_by_sku.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="SKU must be alphanumeric"):
            service.create_product(product_data, tenant_id)

    def test_create_product_invalid_currency(self, service, mock_product_repo):
        """Test product creation fails with invalid currency."""
        # Arrange
        tenant_id = uuid4()
        product_data = ProductCreate(
            tenant_id=tenant_id, sku="TEST-001", name="Test", currency="XXX"
        )
        mock_product_repo.get_by_sku.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Currency.*is not supported"):
            service.create_product(product_data, tenant_id)

    def test_create_product_category_not_found(self, service, mock_product_repo, mock_category_repo):
        """Test product creation fails when category not found."""
        # Arrange
        tenant_id = uuid4()
        category_id = uuid4()
        product_data = ProductCreate(
            tenant_id=tenant_id,
            sku="TEST-001",
            name="Test",
            category_id=category_id,
            currency="USD",
        )
        mock_product_repo.get_by_sku.return_value = None
        mock_category_repo.get_category_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Category.*not found"):
            service.create_product(product_data, tenant_id)

    def test_update_product_success(self, service, mock_product_repo, mock_category_repo):
        """Test successful product update."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        # Use MagicMock to support string formatting
        product = MagicMock()
        product.id = product_id
        product.tenant_id = tenant_id
        product.sku = "TEST-001"
        product.name = "Old Name"
        product.price = Decimal("10.00")
        product.cost = None
        product.weight = None
        product.category_id = None
        product.currency = "USD"
        product.dimensions = None
        product.unit_of_measure = None
        product.track_inventory = True
        product.meta = None
        product.is_active = True
        product.created_at = None
        product.updated_at = None

        mock_product_repo.get_by_id.return_value = product
        mock_product_repo.get_by_sku.return_value = None

        product_data = ProductUpdate(name="New Name")
        # Use the same product object, just update its name
        product.name = "New Name"
        mock_product_repo.update.return_value = product

        # Act
        result = service.update_product(product_id, product_data, tenant_id)

        # Assert
        assert result["name"] == "New Name"
        mock_product_repo.get_by_id.assert_called_once_with(product_id, tenant_id)
        mock_product_repo.update.assert_called_once()

    def test_update_product_not_found(self, service, mock_product_repo):
        """Test update product returns None when product not found."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        product_data = ProductUpdate(name="New Name")
        mock_product_repo.get_by_id.return_value = None

        # Act
        result = service.update_product(product_id, product_data, tenant_id)

        # Assert
        assert result is None

    def test_update_product_duplicate_sku(self, service, mock_product_repo):
        """Test update product fails with duplicate SKU."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        product = Mock()
        product.id = product_id
        product.sku = "TEST-001"
        product.name = "Test"
        product.price = Decimal("10.00")
        product.cost = None
        product.weight = None
        product.category_id = None
        product.currency = "USD"
        product.dimensions = None
        product.unit_of_measure = None
        product.track_inventory = True
        product.meta = None
        product.is_active = True
        product.created_at = None
        product.updated_at = None

        mock_product_repo.get_by_id.return_value = product
        mock_product_repo.get_by_sku.return_value = Mock(sku="TEST-002")

        product_data = ProductUpdate(sku="TEST-002")

        # Act & Assert
        with pytest.raises(ValueError, match="already exists"):
            service.update_product(product_id, product_data, tenant_id)

    def test_delete_product_success(self, service, mock_product_repo):
        """Test successful product soft delete."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        product = Mock()
        product.id = product_id
        product.sku = "TEST-001"
        product.is_active = True
        mock_product_repo.get_by_id.return_value = product
        product.is_active = False
        mock_product_repo.update.return_value = product

        # Act
        result = service.delete_product(product_id, tenant_id)

        # Assert
        assert result is True
        mock_product_repo.get_by_id.assert_called_once_with(product_id, tenant_id)
        mock_product_repo.update.assert_called_once()

    def test_delete_product_not_found(self, service, mock_product_repo):
        """Test delete product returns False when product not found."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        mock_product_repo.get_by_id.return_value = None

        # Act
        result = service.delete_product(product_id, tenant_id)

        # Assert
        assert result is False

    # Category tests
    def test_create_category_success(self, service, mock_category_repo):
        """Test successful category creation."""
        # Arrange
        tenant_id = uuid4()
        category_id = uuid4()
        category_data = CategoryCreate(
            tenant_id=tenant_id, name="Test Category", slug="test-category"
        )
        mock_category_repo.get_category_by_slug.return_value = None
        mock_category = Mock()
        mock_category.id = category_id
        mock_category.name = "Test Category"
        mock_category.slug = "test-category"
        mock_category.description = None
        mock_category.is_active = True
        mock_category.created_at = None
        mock_category.updated_at = None
        mock_category_repo.create_category.return_value = mock_category

        # Act
        result = service.create_category(category_data, tenant_id)

        # Assert
        assert result["name"] == "Test Category"
        mock_category_repo.get_category_by_slug.assert_called_once_with(
            tenant_id, "test-category"
        )
        mock_category_repo.create_category.assert_called_once()

    def test_create_category_duplicate_slug(self, service, mock_category_repo):
        """Test category creation fails with duplicate slug."""
        # Arrange
        tenant_id = uuid4()
        category_data = CategoryCreate(
            tenant_id=tenant_id, name="Test Category", slug="test-category"
        )
        mock_category_repo.get_category_by_slug.return_value = Mock(slug="test-category")

        # Act & Assert
        with pytest.raises(ValueError, match="slug.*already exists"):
            service.create_category(category_data, tenant_id)

    # Variant tests
    def test_create_variant_success(self, service, mock_product_repo, mock_variant_repo):
        """Test successful variant creation."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        variant_id = uuid4()
        product = Mock()
        product.id = product_id
        mock_product_repo.get_by_id.return_value = product
        mock_variant_repo.get_variants_by_product.return_value = []

        variant_data = ProductVariantCreate(
            product_id=product_id, sku="VAR-001", name="Variant 1"
        )
        mock_variant = Mock()
        mock_variant.id = variant_id
        mock_variant.product_id = product_id
        mock_variant.sku = "VAR-001"
        mock_variant.name = "Variant 1"
        mock_variant.price = None
        mock_variant.cost = None
        mock_variant.attributes = None
        mock_variant.image_url = None
        mock_variant.is_active = True
        mock_variant.created_at = None
        mock_variant.updated_at = None
        mock_variant_repo.create_variant.return_value = mock_variant

        # Act
        result = service.create_variant(product_id, variant_data, tenant_id)

        # Assert
        assert result["sku"] == "VAR-001"
        mock_product_repo.get_by_id.assert_called_once_with(product_id, tenant_id)
        mock_variant_repo.create_variant.assert_called_once()

    def test_create_variant_invalid_sku_format(self, service, mock_product_repo, mock_variant_repo):
        """Test variant creation fails with invalid SKU format."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        product = Mock()
        product.id = product_id
        mock_product_repo.get_by_id.return_value = product
        mock_variant_repo.get_variants_by_product.return_value = []

        variant_data = ProductVariantCreate(
            product_id=product_id, sku="SKU WITH SPACES", name="Variant 1"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="SKU must be alphanumeric"):
            service.create_variant(product_id, variant_data, tenant_id)

    def test_create_variant_product_not_found(self, service, mock_product_repo):
        """Test variant creation fails when product not found."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        variant_data = ProductVariantCreate(
            product_id=product_id, sku="VAR-001", name="Variant 1"
        )
        mock_product_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Product.*not found"):
            service.create_variant(product_id, variant_data, tenant_id)

    # Barcode tests
    def test_create_barcode_success(self, service, mock_product_repo, mock_barcode_repo):
        """Test successful barcode creation."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        barcode_id = uuid4()
        product = Mock()
        product.id = product_id
        mock_product_repo.get_by_id.return_value = product
        mock_barcode_repo.get_by_barcode.return_value = None

        barcode_data = ProductBarcodeCreate(
            tenant_id=tenant_id, barcode="1234567890123", barcode_type="EAN13"
        )
        mock_barcode = Mock()
        mock_barcode.id = barcode_id
        mock_barcode.tenant_id = tenant_id
        mock_barcode.product_id = product_id
        mock_barcode.variant_id = None
        mock_barcode.barcode = "1234567890123"
        mock_barcode.barcode_type = "EAN13"
        mock_barcode.is_primary = False
        mock_barcode.created_at = None
        mock_barcode.updated_at = None
        mock_barcode_repo.create_barcode.return_value = mock_barcode

        # Act
        result = service.create_barcode(product_id, None, barcode_data, tenant_id)

        # Assert
        assert result["barcode"] == "1234567890123"
        mock_product_repo.get_by_id.assert_called_once_with(product_id, tenant_id)
        mock_barcode_repo.create_barcode.assert_called_once()

    def test_create_barcode_invalid_ean13(self, service, mock_product_repo, mock_barcode_repo):
        """Test barcode creation fails with invalid EAN13 format."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        product = Mock()
        product.id = product_id
        mock_product_repo.get_by_id.return_value = product
        mock_barcode_repo.get_by_barcode.return_value = None

        barcode_data = ProductBarcodeCreate(
            tenant_id=tenant_id, barcode="12345", barcode_type="EAN13"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="EAN13 barcode must be exactly 13 digits"):
            service.create_barcode(product_id, None, barcode_data, tenant_id)

    def test_create_barcode_duplicate(self, service, mock_product_repo, mock_barcode_repo):
        """Test barcode creation fails with duplicate barcode."""
        # Arrange
        tenant_id = uuid4()
        product_id = uuid4()
        product = Mock()
        product.id = product_id
        mock_product_repo.get_by_id.return_value = product
        mock_barcode_repo.get_by_barcode.return_value = Mock(barcode="1234567890123")

        barcode_data = ProductBarcodeCreate(
            tenant_id=tenant_id, barcode="1234567890123", barcode_type="EAN13"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Barcode.*already exists"):
            service.create_barcode(product_id, None, barcode_data, tenant_id)
