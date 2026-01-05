"""Integration tests for contact methods CRUD operations."""

from uuid import uuid4

import pytest
from fastapi import status

from app.core.auth import hash_password
from app.models.contact_method import ContactMethod, ContactMethodType, EntityType
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import AuthService


class TestContactMethodsAPI:
    """Test suite for contact methods API endpoints."""

    def test_list_contact_methods_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that listing contact methods requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to list contact methods
        response = client.get(
            "/api/v1/contact-methods",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"entity_type": "user", "entity_id": str(test_user.id)},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_list_contact_methods_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can list contact methods."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        # Create a contact method for the user
        contact_method = ContactMethod(
            entity_type=EntityType.USER,
            entity_id=test_user.id,
            method_type=ContactMethodType.EMAIL,
            value="test@example.com",
            label="Test Email",
        )
        db_session.add(contact_method)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List contact methods
        response = client.get(
            "/api/v1/contact-methods",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"entity_type": "user", "entity_id": str(test_user.id)},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 1
        assert data["data"][0]["value"] == "test@example.com"

    def test_list_contact_methods_empty(
        self, client, db_session, test_user, test_tenant
    ):
        """Test listing contact methods when none exist."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List contact methods
        response = client.get(
            "/api/v1/contact-methods",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"entity_type": "user", "entity_id": str(test_user.id)},
        )

        # Assert: Should succeed with empty list
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 0

    def test_create_contact_method_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that creating contact method requires auth.manage_users permission."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to create contact method
        response = client.post(
            "/api/v1/contact-methods",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "entity_type": "user",
                "entity_id": str(test_user.id),
                "method_type": "email",
                "value": "test@example.com",
            },
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_contact_method_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can create contact method."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        test_email = f"test-{uuid4().hex[:8]}@example.com"

        # Act: Create contact method
        response = client.post(
            "/api/v1/contact-methods",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "entity_type": "user",
                "entity_id": str(test_user.id),
                "method_type": "email",
                "value": test_email,
                "label": "Test Email",
                "is_primary": False,
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "data" in data
        assert data["data"]["value"] == test_email
        assert data["data"]["method_type"] == "email"
        assert data["data"]["entity_type"] == "user"
        assert data["data"]["entity_id"] == str(test_user.id)

    def test_create_contact_method_phone(
        self, client, db_session, test_user, test_tenant
    ):
        """Test creating phone contact method."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Create phone contact method
        response = client.post(
            "/api/v1/contact-methods",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "entity_type": "user",
                "entity_id": str(test_user.id),
                "method_type": "phone",
                "value": "+1234567890",
                "label": "Work Phone",
                "is_primary": True,
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["method_type"] == "phone"
        assert data["data"]["value"] == "+1234567890"
        assert data["data"]["is_primary"] is True

    def test_get_contact_method_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that getting contact method requires auth.manage_users permission."""
        # Arrange: Create contact method
        contact_method = ContactMethod(
            entity_type=EntityType.USER,
            entity_id=test_user.id,
            method_type=ContactMethodType.EMAIL,
            value="test@example.com",
        )
        db_session.add(contact_method)
        db_session.commit()

        # User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to get contact method
        response = client.get(
            f"/api/v1/contact-methods/{contact_method.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_contact_method_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can get contact method."""
        # Arrange: Create contact method
        contact_method = ContactMethod(
            entity_type=EntityType.USER,
            entity_id=test_user.id,
            method_type=ContactMethodType.EMAIL,
            value="test@example.com",
            label="Test Email",
        )
        db_session.add(contact_method)
        db_session.commit()

        # Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Get contact method
        response = client.get(
            f"/api/v1/contact-methods/{contact_method.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["id"] == str(contact_method.id)
        assert data["data"]["value"] == "test@example.com"

    def test_get_contact_method_not_found(
        self, client, db_session, test_user, test_tenant
    ):
        """Test getting non-existent contact method."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        fake_id = uuid4()

        # Act: Get non-existent contact method
        response = client.get(
            f"/api/v1/contact-methods/{fake_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_contact_method_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that updating contact method requires auth.manage_users permission."""
        # Arrange: Create contact method
        contact_method = ContactMethod(
            entity_type=EntityType.USER,
            entity_id=test_user.id,
            method_type=ContactMethodType.EMAIL,
            value="test@example.com",
        )
        db_session.add(contact_method)
        db_session.commit()

        # User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to update contact method
        response = client.patch(
            f"/api/v1/contact-methods/{contact_method.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"value": "updated@example.com"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_contact_method_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can update contact method."""
        # Arrange: Create contact method
        contact_method = ContactMethod(
            entity_type=EntityType.USER,
            entity_id=test_user.id,
            method_type=ContactMethodType.EMAIL,
            value="test@example.com",
            label="Original Label",
        )
        db_session.add(contact_method)
        db_session.commit()

        # Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Update contact method
        response = client.patch(
            f"/api/v1/contact-methods/{contact_method.id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "value": "updated@example.com",
                "label": "Updated Label",
                "is_primary": True,
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert data["data"]["value"] == "updated@example.com"
        assert data["data"]["label"] == "Updated Label"
        assert data["data"]["is_primary"] is True

    def test_delete_contact_method_requires_auth_manage_users(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that deleting contact method requires auth.manage_users permission."""
        # Arrange: Create contact method
        contact_method = ContactMethod(
            entity_type=EntityType.USER,
            entity_id=test_user.id,
            method_type=ContactMethodType.EMAIL,
            value="test@example.com",
        )
        db_session.add(contact_method)
        db_session.commit()

        # User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to delete contact method
        response = client.delete(
            f"/api/v1/contact-methods/{contact_method.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_contact_method_with_permission(
        self, client, db_session, test_user, test_tenant
    ):
        """Test that admin can delete contact method."""
        # Arrange: Create contact method
        contact_method = ContactMethod(
            entity_type=EntityType.USER,
            entity_id=test_user.id,
            method_type=ContactMethodType.EMAIL,
            value="test@example.com",
        )
        db_session.add(contact_method)
        db_session.commit()
        contact_method_id = contact_method.id

        # Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Delete contact method
        response = client.delete(
            f"/api/v1/contact-methods/{contact_method_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert "message" in data["data"]

        # Verify it's actually deleted
        deleted = db_session.query(ContactMethod).filter_by(id=contact_method_id).first()
        assert deleted is None

    def test_create_contact_method_address(
        self, client, db_session, test_user, test_tenant
    ):
        """Test creating address contact method with all address fields."""
        # Arrange: Assign admin role
        admin_role = UserRole(
            user_id=test_user.id,
            role="admin",
            granted_by=test_user.id,
        )
        db_session.add(admin_role)
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Create address contact method
        response = client.post(
            "/api/v1/contact-methods",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "entity_type": "user",
                "entity_id": str(test_user.id),
                "method_type": "address",
                "value": "123 Main St",
                "address_line1": "123 Main St",
                "address_line2": "Apt 4B",
                "city": "New York",
                "state_province": "NY",
                "postal_code": "10001",
                "country": "US",
                "label": "Home Address",
            },
        )

        # Assert: Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["data"]["method_type"] == "address"
        assert data["data"]["address_line1"] == "123 Main St"
        assert data["data"]["city"] == "New York"
        assert data["data"]["country"] == "US"

















