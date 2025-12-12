"""Custom exceptions for API error handling."""

from typing import Any

from fastapi import HTTPException, status


class APIException(HTTPException):
    """Custom exception for API errors with standard format.

    Follows the error format defined in rules/api-contract.md and rules/error-handling.md.

    Example:
        raise APIException(
            code="USER_NOT_FOUND",
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize API exception.

        Args:
            code: Error code (e.g., 'AUTH_INVALID_TOKEN', 'USER_NOT_FOUND').
            message: Human-readable error message.
            status_code: HTTP status code (default: 400).
            details: Optional additional error details.
        """
        super().__init__(
            status_code=status_code,
            detail={"error": {"code": code, "message": message, "details": details}},
        )
        self.code = code
        self.message = message
        self.details = details


# Helper functions for common error codes
def raise_not_found(resource: str, resource_id: str | None = None) -> None:
    """Raise 404 Not Found exception.

    Args:
        resource: Resource type (e.g., 'User', 'Product').
        resource_id: Optional resource ID.

    Raises:
        APIException: 404 Not Found error.
    """
    message = f"{resource} not found"
    if resource_id:
        message += f" (ID: {resource_id})"
    raise APIException(
        code=f"{resource.upper().replace(' ', '_')}_NOT_FOUND",
        message=message,
        status_code=status.HTTP_404_NOT_FOUND,
    )


def raise_bad_request(
    code: str, message: str, details: dict[str, Any] | None = None
) -> None:
    """Raise 400 Bad Request exception.

    Args:
        code: Error code.
        message: Error message.
        details: Optional error details.

    Raises:
        APIException: 400 Bad Request error.
    """
    raise APIException(
        code=code,
        message=message,
        status_code=status.HTTP_400_BAD_REQUEST,
        details=details,
    )


def raise_unauthorized(
    code: str = "AUTH_UNAUTHORIZED", message: str = "Unauthorized"
) -> None:
    """Raise 401 Unauthorized exception.

    Args:
        code: Error code (default: 'AUTH_UNAUTHORIZED').
        message: Error message (default: 'Unauthorized').

    Raises:
        APIException: 401 Unauthorized error.
    """
    raise APIException(
        code=code, message=message, status_code=status.HTTP_401_UNAUTHORIZED
    )


def raise_forbidden(
    code: str = "AUTH_INSUFFICIENT_PERMISSIONS",
    message: str = "Insufficient permissions",
    details: dict[str, Any] | None = None,
) -> None:
    """Raise 403 Forbidden exception.

    Args:
        code: Error code (default: 'AUTH_INSUFFICIENT_PERMISSIONS').
        message: Error message (default: 'Insufficient permissions').
        details: Optional error details.

    Raises:
        APIException: 403 Forbidden error.
    """
    raise APIException(
        code=code,
        message=message,
        status_code=status.HTTP_403_FORBIDDEN,
        details=details,
    )


def raise_conflict(
    code: str, message: str, details: dict[str, Any] | None = None
) -> None:
    """Raise 409 Conflict exception.

    Args:
        code: Error code.
        message: Error message.
        details: Optional error details.

    Raises:
        APIException: 409 Conflict error.
    """
    raise APIException(
        code=code,
        message=message,
        status_code=status.HTTP_409_CONFLICT,
        details=details,
    )


def raise_too_many_requests(
    code: str = "AUTH_RATE_LIMIT_EXCEEDED",
    message: str = "Too many requests. Please try again later.",
    details: dict[str, Any] | None = None,
) -> None:
    """Raise 429 Too Many Requests exception.

    Args:
        code: Error code (default: 'AUTH_RATE_LIMIT_EXCEEDED').
        message: Error message (default: 'Too many requests. Please try again later.').
        details: Optional error details.

    Raises:
        APIException: 429 Too Many Requests error.
    """
    raise APIException(
        code=code,
        message=message,
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        details=details,
    )


def raise_internal_server_error(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Raise 500 Internal Server Error exception.

    Args:
        code: Error code.
        message: Error message.
        details: Optional error details.

    Raises:
        APIException: 500 Internal Server Error.
    """
    raise APIException(
        code=code,
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
    )
