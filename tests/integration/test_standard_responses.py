"""Integration tests for standard response formats and exception handling."""

from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import AuthService


class TestStandardResponseFormat:
    """Test that endpoints return StandardResponse format."""

    def test_list_users_returns_standard_list_response(
        self, client_with_db: TestClient, db_session: Session, test_user: User
    ) -> None:
        """Test that GET /api/v1/users returns StandardListResponse format."""
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

        # Act: List users
        response = client_with_db.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return StandardListResponse format
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify StandardListResponse structure
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        assert data["error"] is None
        assert isinstance(data["data"], list)

        # Verify PaginationMeta structure
        assert "total" in data["meta"]
        assert "page" in data["meta"]
        assert "page_size" in data["meta"]
        assert "total_pages" in data["meta"]
        assert isinstance(data["meta"]["total"], int)
        assert isinstance(data["meta"]["page"], int)
        assert isinstance(data["meta"]["page_size"], int)
        assert isinstance(data["meta"]["total_pages"], int)

    def test_get_user_returns_standard_response(
        self, client_with_db: TestClient, db_session: Session, test_user: User
    ) -> None:
        """Test that GET /api/v1/users/{id} returns StandardResponse format."""
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

        # Act: Get user
        response = client_with_db.get(
            f"/api/v1/users/{test_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return StandardResponse format
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify StandardResponse structure
        assert "data" in data
        assert "error" in data
        assert data["error"] is None
        assert isinstance(data["data"], dict)
        assert "id" in data["data"]
        assert "email" in data["data"]

    def test_create_user_returns_standard_response(
        self, client_with_db: TestClient, db_session: Session, test_user: User, test_tenant
    ) -> None:
        """Test that POST /api/v1/users returns StandardResponse format."""
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

        # Act: Create user
        new_email = f"new-{uuid4().hex[:8]}@example.com"
        response = client_with_db.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email": new_email,
                "password": "SecurePass123!",
                "tenant_id": str(test_tenant.id),
            },
        )

        # Assert: Should return StandardResponse format
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        # Verify StandardResponse structure
        assert "data" in data
        assert "error" in data
        assert data["error"] is None
        assert isinstance(data["data"], dict)
        assert data["data"]["email"] == new_email

    def test_list_roles_returns_standard_list_response(
        self, client_with_db: TestClient, db_session: Session, test_user: User
    ) -> None:
        """Test that GET /api/v1/auth/roles returns StandardListResponse format."""
        # Arrange: Authenticated user
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: List roles
        response = client_with_db.get(
            "/api/v1/auth/roles",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return StandardListResponse format
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify StandardListResponse structure
        assert "data" in data
        assert "meta" in data
        assert "error" in data
        assert data["error"] is None
        assert isinstance(data["data"], list)

        # Verify PaginationMeta structure
        assert "total" in data["meta"]
        assert "page" in data["meta"]
        assert "page_size" in data["meta"]
        assert "total_pages" in data["meta"]


class TestAPIExceptionFormat:
    """Test that APIException returns correct error format."""

    def test_not_found_error_format(
        self, client_with_db: TestClient, db_session: Session, test_user: User
    ) -> None:
        """Test that 404 errors return correct format."""
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

        # Act: Get non-existent user
        fake_id = uuid4()
        response = client_with_db.get(
            f"/api/v1/users/{fake_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return correct error format
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        # Verify error format matches API contract
        # Exception handler returns exc.detail directly, which is {"error": {...}}
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]
        assert data["error"]["code"] == "USER_NOT_FOUND"
        assert "User not found" in data["error"]["message"]

    def test_bad_request_error_format(
        self, client_with_db: TestClient, db_session: Session, test_user: User, test_tenant
    ) -> None:
        """Test that 400 errors return correct format."""
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

        # Act: Try to create user with existing email
        response = client_with_db.post(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "email": test_user.email,  # Already exists
                "password": "SecurePass123!",
                "tenant_id": str(test_tenant.id),
            },
        )

        # Assert: Should return correct error format
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()

        # Verify error format matches API contract
        # Exception handler returns exc.detail directly, which is {"error": {...}}
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]
        assert data["error"]["code"] == "USER_ALREADY_EXISTS"

    def test_forbidden_error_format(
        self, client_with_db: TestClient, db_session: Session, test_user: User
    ) -> None:
        """Test that 403 errors return correct format."""
        # Arrange: User without admin role
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        # Act: Try to list users without permission
        response = client_with_db.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return correct error format
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()

        # Verify error format matches API contract
        # Exception handler returns exc.detail directly, which is {"error": {...}}
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]
        assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"

    def test_unauthorized_error_format(
        self, client_with_db: TestClient, test_user: User
    ) -> None:
        """Test that 401 errors return correct format."""
        # Act: Try to login with invalid credentials
        response = client_with_db.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrong_password",
            },
        )

        # Assert: Should return correct error format
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        # Verify error format matches API contract
        # Exception handler returns exc.detail directly, which is {"error": {...}}
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "details" in data["error"]
        assert data["error"]["code"] == "AUTH_INVALID_CREDENTIALS"

    def test_exception_handler_works_globally(
        self, client_with_db: TestClient, db_session: Session, test_user: User
    ) -> None:
        """Test that exception handler works globally for all APIException."""
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

        # Act: Try to access user from different tenant (should raise APIException)
        # First create another tenant and user
        from app.models.tenant import Tenant

        other_tenant = Tenant(
            name="Other Tenant",
            slug="other-tenant",
        )
        db_session.add(other_tenant)
        db_session.commit()
        db_session.refresh(other_tenant)

        other_user = User(
            email=f"other-{uuid4().hex[:8]}@example.com",
            password_hash=hash_password("password123"),
            full_name="Other User",
            tenant_id=other_tenant.id,
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Try to access user from different tenant
        response = client_with_db.get(
            f"/api/v1/users/{other_user.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assert: Should return correct error format via exception handler
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()

        # Verify error format matches API contract
        # Exception handler returns exc.detail directly, which is {"error": {...}}
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert data["error"]["code"] == "AUTH_TENANT_MISMATCH"
