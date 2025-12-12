"""Integration tests for products module CRUD operations."""

from uuid import uuid4

from fastapi import status

from app.models.module_role import ModuleRole
from app.models.user import User
from app.services.auth_service import AuthService


class TestProducts:
    """Test suite for products functionality."""

    def test_list_products_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that listing products requires products.view permission."""
        # Arrange: User without products permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to list products
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        # FastAPI wraps HTTPException in "detail" field
        assert "detail" in data or "error" in data
        if "detail" in data:
            assert "error" in data["detail"]
            assert data["detail"]["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"
        else:
            assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_list_products_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that user with products.view can list products."""
        # Arrange: Assign products.viewer role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List products
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)
        assert data["meta"]["total"] >= 0

    def test_create_product_requires_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that creating product requires products.create permission."""
        # Arrange: User without products.create permission
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to create product
        response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Test Product",
                "price": "10.00",
                "currency": "USD",
            },
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that user with products.create can create product."""
        # Arrange: Assign products.editor role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        sku = f"SKU-{uuid4().hex[:8]}"

        # Act: Create product
        response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": sku,
                "name": "Test Product",
                "description": "Test Description",
                "price": "10.00",
                "cost": "5.00",
                "currency": "USD",
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert data["data"]["sku"] == sku
        assert data["data"]["name"] == "Test Product"
        assert data["data"]["is_active"] is True

    def test_create_product_duplicate_sku(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that creating product with duplicate SKU fails."""
        # Arrange: Assign products.editor role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        sku = f"SKU-{uuid4().hex[:8]}"

        # Create first product
        client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": sku,
                "name": "First Product",
                "price": "10.00",
                "currency": "USD",
            },
        )

        # Act: Try to create product with same SKU
        response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": sku,
                "name": "Second Product",
                "price": "20.00",
                "currency": "USD",
            },
        )

        # Assert: Should fail with conflict
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        # APIException handler returns {"error": {...}, "data": None}
        assert "error" in data
        assert data["error"]["code"] == "PRODUCT_ALREADY_EXISTS"

    def test_get_product_by_id(self, client, db_session, test_user, test_tenant):
        """Test getting product by ID."""
        # Arrange: Assign products.viewer role for reading and editor for creating
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product
        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Test Product",
                "price": "10.00",
                "currency": "USD",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        # Act: Get product
        response = client.get(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == product_id

    def test_get_product_not_found(self, client, db_session, test_user, test_tenant):
        """Test getting non-existent product returns 404."""
        # Arrange: Assign products.viewer role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        fake_id = str(uuid4())

        # Act: Get non-existent product
        response = client.get(
            f"/api/v1/products/{fake_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_product(self, client, db_session, test_user, test_tenant):
        """Test updating product."""
        # Arrange: Assign products.editor role and create product
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product
        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Original Name",
                "price": "10.00",
                "currency": "USD",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        # Act: Update product
        response = client.patch(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "Updated Name",
                "price": "15.00",
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["price"] == "15.00"

    def test_delete_product_soft_delete(
        self, client, db_session, test_user, test_tenant
    ):
        """Test soft delete product."""
        # Arrange: Assign products.editor role for creation and products.delete for deletion
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        delete_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="manager",  # manager role has products.delete permission
            granted_by=test_user.id,
        )
        db_session.add(editor_role)
        db_session.add(delete_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product
        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Product to Delete",
                "price": "10.00",
                "currency": "USD",
            },
        )
        product_id = create_response.json()["data"]["id"]

        # Act: Delete product
        response = client.delete(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK

        # Verify product is soft deleted (is_active=False)
        get_response = client.get(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["data"]["is_active"] is False

    def test_list_products_with_filters(
        self, client, db_session, test_user, test_tenant
    ):
        """Test listing products with category and search filters."""
        # Arrange: Assign products.viewer role for reading and editor for creating
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create category
        category_response = client.post(
            "/api/v1/products/categories",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "name": "Electronics",
                "slug": "electronics",
            },
        )
        assert category_response.status_code == status.HTTP_201_CREATED
        category_id = category_response.json()["data"]["id"]

        # Create products
        client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Laptop",
                "category_id": category_id,
                "price": "1000.00",
                "currency": "USD",
            },
        )

        # Act: List products with category filter
        response = client.get(
            f"/api/v1/products?category_id={category_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1

        # Act: Search products
        search_response = client.get(
            "/api/v1/products?search=Laptop",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should find products
        assert search_response.status_code == status.HTTP_200_OK
        search_data = search_response.json()
        assert len(search_data["data"]) >= 1

    def test_products_isolated_by_tenant(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that products are isolated by tenant."""
        # Arrange: Create second tenant and user
        from app.models.tenant import Tenant

        tenant2 = Tenant(
            name="Test Tenant 2",
            slug=f"test-tenant-2-{uuid4().hex[:8]}",
        )
        db_session.add(tenant2)
        db_session.commit()

        from app.core.auth import hash_password

        user2 = User(
            email=f"user2-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password"),
            tenant_id=tenant2.id,
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()

        # Assign products.viewer to both users
        module_role1 = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        module_role2 = ModuleRole(
            user_id=user2.id,
            module="products",
            role_name="viewer",
            granted_by=user2.id,
        )
        db_session.add(module_role1)
        db_session.add(module_role2)
        db_session.commit()

        auth_service = AuthService(db_session)
        token1 = auth_service.create_access_token_for_user(test_user)
        token2 = auth_service.create_access_token_for_user(user2)

        # Create product in tenant1 (user1 needs editor role)
        editor_role1 = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(editor_role1)
        db_session.commit()

        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Tenant 1 Product",
                "price": "10.00",
                "currency": "USD",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        # Act: User2 tries to access tenant1's product
        response = client.get(
            f"/api/v1/products/{product_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )

        # Assert: Should return 404 (not found in tenant2)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_products_returns_standard_format(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that list products returns standard response format."""
        # Arrange: Assign products.viewer role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List products
        response = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should have standard format
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        assert data["error"] is None
        assert "total" in data["meta"]
        assert "page" in data["meta"]
        assert "page_size" in data["meta"]
        assert "total_pages" in data["meta"]


class TestCategories:
    """Test suite for categories functionality."""

    def test_list_categories(self, client, db_session, test_user, test_tenant):
        """Test listing categories."""
        # Arrange: Assign products.viewer role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List categories
        response = client.get(
            "/api/v1/products/categories",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_create_category(self, client, db_session, test_user, test_tenant):
        """Test creating category."""
        # Arrange: Assign products.editor role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Create category
        response = client.post(
            "/api/v1/products/categories",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "name": "Electronics",
                "slug": f"electronics-{uuid4().hex[:8]}",
                "description": "Electronic products",
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert data["data"]["name"] == "Electronics"

    def test_create_category_duplicate_slug(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that creating category with duplicate slug fails."""
        # Arrange: Assign products.editor role
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        slug = f"electronics-{uuid4().hex[:8]}"

        # Create first category
        client.post(
            "/api/v1/products/categories",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "name": "Electronics",
                "slug": slug,
            },
        )

        # Act: Try to create category with same slug
        response = client.post(
            "/api/v1/products/categories",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "name": "Electronics 2",
                "slug": slug,
            },
        )

        # Assert: Should fail with conflict
        assert response.status_code == status.HTTP_409_CONFLICT


class TestVariants:
    """Test suite for product variants functionality."""

    def test_list_variants(self, client, db_session, test_user, test_tenant):
        """Test listing variants for a product."""
        # Arrange: Assign products.viewer role for reading and editor for creating
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product
        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Test Product",
                "price": "10.00",
                "currency": "USD",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        # Act: List variants
        response = client.get(
            f"/api/v1/products/{product_id}/variants",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_create_variant(self, client, db_session, test_user, test_tenant):
        """Test creating variant."""
        # Arrange: Assign products.editor role and create product
        module_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(module_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product
        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Test Product",
                "price": "10.00",
                "currency": "USD",
            },
        )
        product_id = create_response.json()["data"]["id"]

        # Act: Create variant
        response = client.post(
            f"/api/v1/products/{product_id}/variants",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "product_id": product_id,
                "sku": f"SKU-VAR-{uuid4().hex[:8]}",
                "name": "Red - Large",
                "price": "12.00",
                "attributes": {"color": "red", "size": "L"},
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert data["data"]["name"] == "Red - Large"


class TestBarcodes:
    """Test suite for product barcodes functionality."""

    def test_get_by_barcode(self, client, db_session, test_user, test_tenant):
        """Test getting product by barcode."""
        # Arrange: Assign products.viewer role for reading and editor for creating
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product
        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Test Product",
                "price": "10.00",
                "currency": "USD",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        barcode = "1234567890123"

        # Create barcode
        client.post(
            f"/api/v1/products/{product_id}/barcodes",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "barcode": barcode,
                "barcode_type": "EAN13",
                "is_primary": True,
            },
        )

        # Act: Get by barcode
        response = client.get(
            f"/api/v1/products/by-barcode/{barcode}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "barcode" in data["data"]
        assert data["data"]["barcode"] == barcode

    def test_list_barcodes(self, client, db_session, test_user, test_tenant):
        """Test listing barcodes for a product."""
        # Arrange: Assign products.viewer role for reading and editor for creating
        viewer_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="viewer",
            granted_by=test_user.id,
        )
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(viewer_role)
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product
        create_response = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "sku": f"SKU-{uuid4().hex[:8]}",
                "name": "Test Product",
                "price": "10.00",
                "currency": "USD",
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        # Create barcode
        client.post(
            f"/api/v1/products/{product_id}/barcodes",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "tenant_id": str(test_tenant.id),
                "barcode": "1234567890123",
                "barcode_type": "EAN13",
            },
        )

        # Act: List barcodes
        response = client.get(
            f"/api/v1/products/{product_id}/barcodes",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert len(data["data"]) >= 1


class TestProductValidations:
    """Test suite for product validation edge cases."""

    def test_create_product_invalid_sku_format(self, client, db_session, test_user, test_tenant):
        """Test product creation fails with invalid SKU format."""
        # Arrange
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        product_data = {
            "tenant_id": str(test_tenant.id),
            "sku": "SKU WITH SPACES",  # Inválido
            "name": "Test Product",
            "currency": "USD",
        }

        # Act
        response = client.post(
            "/api/v1/products",
            json=product_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "SKU" in data["error"]["message"] or "alphanumeric" in data["error"]["message"]

    def test_create_product_invalid_currency(self, client, db_session, test_user, test_tenant):
        """Test product creation fails with invalid currency."""
        # Arrange
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        product_data = {
            "tenant_id": str(test_tenant.id),
            "sku": "TEST-001",
            "name": "Test Product",
            "currency": "XXX",  # No soportado
        }

        # Act
        response = client.post(
            "/api/v1/products",
            json=product_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "Currency" in data["error"]["message"] or "not supported" in data["error"]["message"]

    def test_create_barcode_invalid_ean13(self, client, db_session, test_user, test_tenant):
        """Test barcode creation fails with invalid EAN13 format."""
        # Arrange
        editor_role = ModuleRole(
            user_id=test_user.id,
            module="products",
            role_name="editor",
            granted_by=test_user.id,
        )
        db_session.add(editor_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create product first
        product_data = {
            "tenant_id": str(test_tenant.id),
            "sku": "PROD-001",
            "name": "Test Product",
            "currency": "USD",
        }
        create_response = client.post(
            "/api/v1/products",
            json=product_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        product_id = create_response.json()["data"]["id"]

        # Try to create barcode with invalid EAN13
        barcode_data = {
            "tenant_id": str(test_tenant.id),
            "barcode": "12345",  # EAN13 debe tener 13 dígitos
            "barcode_type": "EAN13",
        }

        # Act
        response = client.post(
            f"/api/v1/products/{product_id}/barcodes",
            json=barcode_data,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data
        assert "EAN13" in data["error"]["message"] or "13 digits" in data["error"]["message"]
