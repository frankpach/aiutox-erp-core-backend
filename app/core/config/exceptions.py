"""Custom exceptions for configuration module."""

from fastapi import status

from app.core.exceptions import APIException


class InvalidColorFormatException(APIException):
    """Exception raised when a color format is invalid.

    Args:
        key: Configuration key (e.g., 'primary_color').
        value: Invalid color value that was provided.
    """

    def __init__(self, key: str, value: str) -> None:
        """Initialize invalid color format exception.

        Args:
            key: Configuration key (e.g., 'primary_color').
            value: Invalid color value that was provided.
        """
        message = f"Invalid color format for '{key}': must be #RRGGBB (got: {value})"
        super().__init__(
            code="INVALID_COLOR_FORMAT",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "key": key,
                "value": value,
                "expected_format": "#RRGGBB",
            },
        )












