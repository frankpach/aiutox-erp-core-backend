"""Integration tests for inventory module."""

from decimal import Decimal
from uuid import uuid4

from fastapi import status

from app.models.module_role import ModuleRole
from app.modules.products.models.product import Product
from app.services.auth_service import AuthService


class TestInventory:
    def test_list_warehouses_requires_permission(
        self, client_with_db, db_session, test_user
    ):
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        response = client_with_db.get(
            "/api/v1/inventory/warehouses",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_warehouses_with_permission(
        self, client_with_db, db_session, test_user
    ):
        db_session.add(
            ModuleRole(
                user_id=test_user.id,
                module="inventory",
                role_name="viewer",
                granted_by=test_user.id,
            )
        )
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        response = client_with_db.get(
            "/api/v1/inventory/warehouses",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert "data" in payload

    def test_create_warehouse_requires_permission(
        self, client_with_db, db_session, test_user
    ):
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        response = client_with_db.post(
            "/api/v1/inventory/warehouses",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Main", "code": "MAIN"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_stock_move_with_permission(
        self, client_with_db, db_session, test_user, test_tenant
    ):
        db_session.add(
            ModuleRole(
                user_id=test_user.id,
                module="inventory",
                role_name="editor",
                granted_by=test_user.id,
            )
        )
        db_session.commit()

        # Create a product (FK target)
        product = Product(
            tenant_id=test_tenant.id,
            sku=f"SKU-{uuid4().hex[:8]}",
            name="Test Product",
            currency="USD",
            is_active=True,
            track_inventory=True,
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Create warehouse
        wh_resp = client_with_db.post(
            "/api/v1/inventory/warehouses",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Main", "code": "MAIN"},
        )
        assert wh_resp.status_code == status.HTTP_201_CREATED
        warehouse_id = wh_resp.json()["data"]["id"]

        # Create location
        loc_resp = client_with_db.post(
            f"/api/v1/inventory/warehouses/{warehouse_id}/locations",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Stock", "code": "STOCK"},
        )
        assert loc_resp.status_code == status.HTTP_201_CREATED
        location_id = loc_resp.json()["data"]["id"]

        # Create stock move (receipt into location)
        move_resp = client_with_db.post(
            "/api/v1/inventory/stock-moves",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "product_id": str(product.id),
                "from_location_id": None,
                "to_location_id": location_id,
                "quantity": str(Decimal("5")),
                "unit_cost": str(Decimal("10")),
                "move_type": "receipt",
                "reference": "PO-1",
            },
        )
        assert move_resp.status_code == status.HTTP_201_CREATED
        data = move_resp.json()["data"]
        assert data["product_id"] == str(product.id)
        assert data["to_location_id"] == location_id
        assert data["move_type"] == "receipt"
