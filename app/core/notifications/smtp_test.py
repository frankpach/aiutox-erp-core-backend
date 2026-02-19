"""SMTP connection testing functionality."""

import logging
from dataclasses import dataclass
from smtplib import (
    SMTP,
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPException,
    SMTPServerDisconnected,
)
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SMTPTestResult:
    """Result of SMTP connection test."""

    success: bool
    message: str
    error: str | None = None
    details: dict[str, Any] | None = None


def check_smtp_connection(config: dict[str, Any]) -> SMTPTestResult:
    """Test SMTP connection with provided configuration.

    Args:
        config: SMTP configuration dictionary with keys:
            - host: SMTP server hostname (required)
            - port: SMTP server port (required, 1-65535)
            - user: SMTP username (optional, for authentication)
            - password: SMTP password (optional, for authentication)
            - use_tls: Whether to use TLS encryption (default: True)
            - timeout: Connection timeout in seconds (default: 10)

    Returns:
        SMTPTestResult with success status, message, and optional error details.

    Raises:
        ValueError: If required configuration fields are missing or invalid.
    """
    # Validate required fields
    host = config.get("host")
    port = config.get("port")

    if not host:
        return SMTPTestResult(
            success=False,
            message="SMTP host is required",
            error="Missing required field: host",
        )

    if not port or not isinstance(port, int) or not (1 <= port <= 65535):
        return SMTPTestResult(
            success=False,
            message="SMTP port must be a valid integer between 1 and 65535",
            error=f"Invalid port: {port}",
        )

    use_tls = config.get("use_tls", True)
    timeout = config.get("timeout", 10)
    user = config.get("user")
    password = config.get("password")

    # Security: Validate timeout to prevent DoS
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 60:
        timeout = 10  # Default safe timeout

    try:
        # Create SMTP connection
        with SMTP(host, port, timeout=timeout) as server:
            # Enable TLS if configured
            if use_tls:
                try:
                    server.starttls()
                except SMTPServerDisconnected as e:
                    return SMTPTestResult(
                        success=False,
                        message="SMTP server disconnected during TLS handshake",
                        error=f"Server disconnected: {str(e)}",
                        details={"host": host, "port": port, "use_tls": use_tls},
                    )
                except SMTPException as e:
                    return SMTPTestResult(
                        success=False,
                        message="Failed to establish TLS connection",
                        error=f"TLS error: {str(e)}",
                        details={"host": host, "port": port, "use_tls": use_tls},
                    )

            # Authenticate if credentials provided
            if user and password:
                try:
                    server.login(user, password)
                except SMTPAuthenticationError as e:
                    return SMTPTestResult(
                        success=False,
                        message="SMTP authentication failed",
                        error=f"Authentication error ({e.smtp_code}): {e.smtp_error.decode('utf-8', errors='ignore') if isinstance(e.smtp_error, bytes) else str(e.smtp_error)}",
                        details={"host": host, "port": port, "user": user},
                    )
                except SMTPException as e:
                    return SMTPTestResult(
                        success=False,
                        message="SMTP authentication error",
                        error=f"Auth error: {str(e)}",
                        details={"host": host, "port": port},
                    )

            # Connection successful
            return SMTPTestResult(
                success=True,
                message="SMTP connection test successful",
                details={
                    "host": host,
                    "port": port,
                    "use_tls": use_tls,
                    "authenticated": bool(user and password),
                },
            )

    except SMTPConnectError as e:
        return SMTPTestResult(
            success=False,
            message="Failed to connect to SMTP server",
            error=f"Connection error ({e.smtp_code}): {e.smtp_error.decode('utf-8', errors='ignore') if isinstance(e.smtp_error, bytes) else str(e.smtp_error)}",
            details={"host": host, "port": port},
        )
    except TimeoutError as e:
        return SMTPTestResult(
            success=False,
            message="SMTP connection timed out",
            error=f"Timeout after {timeout} seconds: {str(e)}",
            details={"host": host, "port": port, "timeout": timeout},
        )
    except OSError as e:
        # Network errors (DNS resolution, network unreachable, etc.)
        return SMTPTestResult(
            success=False,
            message="Network error connecting to SMTP server",
            error=f"Network error: {str(e)}",
            details={"host": host, "port": port},
        )
    except SMTPException as e:
        return SMTPTestResult(
            success=False,
            message="SMTP error occurred",
            error=f"SMTP error: {str(e)}",
            details={"host": host, "port": port},
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception("Unexpected error during SMTP connection test")
        return SMTPTestResult(
            success=False,
            message="Unexpected error during SMTP connection test",
            error=f"Unexpected error: {str(e)}",
            details={"host": host, "port": port},
        )











