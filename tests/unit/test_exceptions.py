"""Unit tests for API exceptions."""

import pytest
from fastapi import status

from app.core.exceptions import (
    APIException,
    raise_bad_request,
    raise_conflict,
    raise_forbidden,
    raise_not_found,
    raise_unauthorized,
)


class TestAPIException:
    """Tests for APIException class."""

    def test_api_exception_default_status(self) -> None:
        """Test APIException with default status code."""
        exc = APIException(code="TEST_ERROR", message="Test error")
        assert exc.code == "TEST_ERROR"
        assert exc.message == "Test error"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.details is None
        assert exc.detail == {
            "error": {"code": "TEST_ERROR", "message": "Test error", "details": None}
        }

    def test_api_exception_custom_status(self) -> None:
        """Test APIException with custom status code."""
        exc = APIException(
            code="NOT_FOUND",
            message="Resource not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_api_exception_with_details(self) -> None:
        """Test APIException with additional details."""
        details = {"field": "email", "reason": "invalid"}
        exc = APIException(
            code="VALIDATION_ERROR", message="Validation failed", details=details
        )
        assert exc.details == details
        assert exc.detail["error"]["details"] == details


class TestHelperFunctions:
    """Tests for exception helper functions."""

    def test_raise_not_found(self) -> None:
        """Test raise_not_found helper."""
        with pytest.raises(APIException) as exc_info:
            raise_not_found("User", "123")
        assert exc_info.value.code == "USER_NOT_FOUND"
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in exc_info.value.message
        assert "123" in exc_info.value.message

    def test_raise_not_found_without_id(self) -> None:
        """Test raise_not_found without resource ID."""
        with pytest.raises(APIException) as exc_info:
            raise_not_found("Product")
        assert exc_info.value.code == "PRODUCT_NOT_FOUND"
        assert "Product not found" in exc_info.value.message

    def test_raise_bad_request(self) -> None:
        """Test raise_bad_request helper."""
        with pytest.raises(APIException) as exc_info:
            raise_bad_request("INVALID_INPUT", "Invalid data provided")
        assert exc_info.value.code == "INVALID_INPUT"
        assert exc_info.value.message == "Invalid data provided"
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_raise_bad_request_with_details(self) -> None:
        """Test raise_bad_request with details."""
        details = {"field": "email"}
        with pytest.raises(APIException) as exc_info:
            raise_bad_request("VALIDATION_ERROR", "Validation failed", details=details)
        assert exc_info.value.details == details

    def test_raise_unauthorized(self) -> None:
        """Test raise_unauthorized helper."""
        with pytest.raises(APIException) as exc_info:
            raise_unauthorized()
        assert exc_info.value.code == "AUTH_UNAUTHORIZED"
        assert exc_info.value.message == "Unauthorized"
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_raise_unauthorized_custom(self) -> None:
        """Test raise_unauthorized with custom code and message."""
        with pytest.raises(APIException) as exc_info:
            raise_unauthorized("AUTH_INVALID_TOKEN", "Invalid token")
        assert exc_info.value.code == "AUTH_INVALID_TOKEN"
        assert exc_info.value.message == "Invalid token"

    def test_raise_forbidden(self) -> None:
        """Test raise_forbidden helper."""
        with pytest.raises(APIException) as exc_info:
            raise_forbidden()
        assert exc_info.value.code == "AUTH_INSUFFICIENT_PERMISSIONS"
        assert exc_info.value.message == "Insufficient permissions"
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_raise_forbidden_with_details(self) -> None:
        """Test raise_forbidden with details."""
        details = {"required_permission": "admin.access"}
        with pytest.raises(APIException) as exc_info:
            raise_forbidden(details=details)
        assert exc_info.value.details == details

    def test_raise_conflict(self) -> None:
        """Test raise_conflict helper."""
        with pytest.raises(APIException) as exc_info:
            raise_conflict("USER_ALREADY_EXISTS", "User already exists")
        assert exc_info.value.code == "USER_ALREADY_EXISTS"
        assert exc_info.value.message == "User already exists"
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT




