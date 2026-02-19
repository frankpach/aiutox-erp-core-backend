"""Common schemas for standard API responses."""

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"total": 100, "page": 1, "page_size": 20, "total_pages": 5}
        }
    )

    total: int = Field(..., description="Total number of items", ge=0)
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Number of items per page", ge=1, le=100)
    total_pages: int = Field(..., description="Total number of pages", ge=0)


class StandardResponse[T](BaseModel):
    """Standard response wrapper for single resources.

    Follows the API contract defined in rules/api-contract.md.
    """

    model_config = ConfigDict(
        json_schema_extra={"example": {"data": {}, "meta": None, "error": None}}
    )

    data: T = Field(..., description="Response data")
    meta: dict | None = Field(None, description="Optional metadata")
    error: None = Field(None, description="Error object (null on success)")


class StandardListResponse[T](BaseModel):
    """Standard response wrapper for collections with pagination.

    Follows the API contract defined in rules/api-contract.md.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [],
                "meta": {"total": 100, "page": 1, "page_size": 20, "total_pages": 5},
                "error": None,
            }
        }
    )

    data: list[T] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata")
    error: None = Field(None, description="Error object (null on success)")


class ErrorDetail(BaseModel):
    """Error detail schema following API contract."""

    code: str = Field(..., description="Error code (e.g., 'AUTH_INVALID_TOKEN')")
    message: str = Field(..., description="Human-readable error message")
    details: dict | None = Field(None, description="Additional error details")

    model_config = {
        "json_schema_extra": {
            "example": {
                "code": "AUTH_INVALID_TOKEN",
                "message": "Invalid token",
                "details": None,
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response schema following API contract."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "AUTH_INVALID_TOKEN",
                    "message": "Invalid token",
                    "details": None,
                },
                "data": None,
            }
        }
    )

    error: ErrorDetail = Field(..., description="Error information")
    data: None = Field(None, description="Data object (null on error)")


# Rebuild models to ensure Generic types work correctly with FastAPI
# StandardResponse.model_rebuild()
# StandardListResponse.model_rebuild()
