"""Unit tests for common schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    PaginationMeta,
    StandardListResponse,
    StandardResponse,
)


class TestPaginationMeta:
    """Tests for PaginationMeta schema."""

    def test_valid_pagination_meta(self) -> None:
        """Test creating valid PaginationMeta."""
        meta = PaginationMeta(total=100, page=1, page_size=20, total_pages=5)
        assert meta.total == 100
        assert meta.page == 1
        assert meta.page_size == 20
        assert meta.total_pages == 5

    def test_pagination_meta_with_zero_total(self) -> None:
        """Test PaginationMeta with zero total."""
        meta = PaginationMeta(total=0, page=1, page_size=20, total_pages=0)
        assert meta.total == 0
        assert meta.total_pages == 0

    def test_pagination_meta_invalid_total(self) -> None:
        """Test PaginationMeta with negative total."""
        with pytest.raises(ValidationError):
            PaginationMeta(total=-1, page=1, page_size=20, total_pages=0)

    def test_pagination_meta_invalid_page(self) -> None:
        """Test PaginationMeta with invalid page."""
        with pytest.raises(ValidationError):
            PaginationMeta(total=100, page=0, page_size=20, total_pages=5)


class TestStandardResponse:
    """Tests for StandardResponse schema."""

    def test_standard_response_with_dict(self) -> None:
        """Test StandardResponse with dict data."""
        data = {"id": "123", "name": "Test"}
        response = StandardResponse(data=data)
        assert response.data == data
        assert response.meta is None
        assert response.error is None

    def test_standard_response_with_meta(self) -> None:
        """Test StandardResponse with metadata."""
        data = {"id": "123"}
        meta = {"timestamp": "2025-01-01"}
        response = StandardResponse(data=data, meta=meta)
        assert response.data == data
        assert response.meta == meta

    def test_standard_response_serialization(self) -> None:
        """Test StandardResponse serialization."""
        data = {"id": "123", "name": "Test"}
        response = StandardResponse(data=data)
        serialized = response.model_dump()
        assert serialized["data"] == data
        assert serialized["meta"] is None
        assert serialized["error"] is None


class TestStandardListResponse:
    """Tests for StandardListResponse schema."""

    def test_standard_list_response(self) -> None:
        """Test StandardListResponse with list data."""
        data = [{"id": "1"}, {"id": "2"}]
        meta = PaginationMeta(total=100, page=1, page_size=20, total_pages=5)
        response = StandardListResponse(data=data, meta=meta)
        assert len(response.data) == 2
        assert response.meta.total == 100
        assert response.meta.page == 1

    def test_standard_list_response_empty(self) -> None:
        """Test StandardListResponse with empty list."""
        data: list[dict] = []
        meta = PaginationMeta(total=0, page=1, page_size=20, total_pages=0)
        response = StandardListResponse(data=data, meta=meta)
        assert len(response.data) == 0
        assert response.meta.total == 0

    def test_standard_list_response_serialization(self) -> None:
        """Test StandardListResponse serialization."""
        data = [{"id": "1"}]
        meta = PaginationMeta(total=1, page=1, page_size=20, total_pages=1)
        response = StandardListResponse(data=data, meta=meta)
        serialized = response.model_dump()
        assert len(serialized["data"]) == 1
        assert serialized["meta"]["total"] == 1


class TestErrorDetail:
    """Tests for ErrorDetail schema."""

    def test_error_detail(self) -> None:
        """Test creating ErrorDetail."""
        error = ErrorDetail(code="TEST_ERROR", message="Test error message")
        assert error.code == "TEST_ERROR"
        assert error.message == "Test error message"
        assert error.details is None

    def test_error_detail_with_details(self) -> None:
        """Test ErrorDetail with additional details."""
        details = {"field": "email", "reason": "invalid format"}
        error = ErrorDetail(
            code="VALIDATION_ERROR", message="Validation failed", details=details
        )
        assert error.details == details


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_error_response(self) -> None:
        """Test creating ErrorResponse."""
        error_detail = ErrorDetail(code="TEST_ERROR", message="Test error")
        response = ErrorResponse(error=error_detail)
        assert response.error.code == "TEST_ERROR"
        assert response.data is None

    def test_error_response_serialization(self) -> None:
        """Test ErrorResponse serialization."""
        error_detail = ErrorDetail(code="TEST_ERROR", message="Test error")
        response = ErrorResponse(error=error_detail)
        serialized = response.model_dump()
        assert serialized["error"]["code"] == "TEST_ERROR"
        assert serialized["data"] is None





