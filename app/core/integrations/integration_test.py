"""Integration testing functionality for various integration types."""

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from app.models.integration import IntegrationType

logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestResult:
    """Result of an integration connection test."""

    success: bool
    message: str
    error: str | None = None
    details: dict[str, Any] | None = None


def test_rest_api_integration(config: dict[str, Any]) -> IntegrationTestResult:
    """
    Test REST API integration by making a test request.

    Args:
        config: Dictionary containing REST API configuration:
            - url: API endpoint URL (required)
            - method: HTTP method (default: GET)
            - headers: Request headers (optional)
            - auth_type: Authentication type ('bearer', 'basic', 'api_key', None)
            - auth_token: Bearer token or API key (optional)
            - username: Basic auth username (optional)
            - password: Basic auth password (optional)
            - timeout: Request timeout in seconds (default: 10)

    Returns:
        IntegrationTestResult indicating success or failure and details.
    """
    url = config.get("url")
    if not url:
        return IntegrationTestResult(
            success=False,
            message="API URL is required",
            error="Missing url",
        )

    method = config.get("method", "GET").upper()
    timeout = config.get("timeout", 10)
    headers = config.get("headers", {})

    # Security: Validate timeout to prevent DoS
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 60:
        timeout = 10  # Default safe timeout

    # Setup authentication
    auth_type = config.get("auth_type")
    if auth_type == "bearer":
        token = config.get("auth_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic":
        username = config.get("username")
        password = config.get("password")
        if username and password:
            import base64

            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
    elif auth_type == "api_key":
        api_key = config.get("auth_token")
        api_key_header = config.get("api_key_header", "X-API-Key")
        if api_key:
            headers[api_key_header] = api_key

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, headers=headers)

            if response.status_code < 400:
                return IntegrationTestResult(
                    success=True,
                    message=f"REST API connection test successful (status: {response.status_code})",
                    details={
                        "url": url,
                        "method": method,
                        "status_code": response.status_code,
                        "response_size": len(response.content),
                    },
                )
            else:
                return IntegrationTestResult(
                    success=False,
                    message=f"REST API returned error status: {response.status_code}",
                    error=f"HTTP {response.status_code}",
                    details={
                        "url": url,
                        "method": method,
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] if response.text else None,
                    },
                )

    except httpx.TimeoutException:
        return IntegrationTestResult(
            success=False,
            message="REST API connection timed out",
            error=f"Timeout after {timeout} seconds",
            details={"url": url, "timeout": timeout},
        )
    except httpx.ConnectError as e:
        return IntegrationTestResult(
            success=False,
            message="Failed to connect to REST API endpoint",
            error=f"Connection error: {str(e)}",
            details={"url": url},
        )
    except Exception as e:
        logger.error(f"Unexpected error during REST API test: {e}", exc_info=True)
        return IntegrationTestResult(
            success=False,
            message="Unexpected error during REST API connection test",
            error=f"Unexpected error: {str(e)}",
            details={"url": url},
        )


def test_webhook_integration(config: dict[str, Any]) -> IntegrationTestResult:
    """
    Test webhook integration by sending a test payload.

    Args:
        config: Dictionary containing webhook configuration:
            - url: Webhook URL (required)
            - method: HTTP method (default: POST)
            - headers: Request headers (optional)
            - secret: Webhook secret for signature (optional)
            - timeout: Request timeout in seconds (default: 10)

    Returns:
        IntegrationTestResult indicating success or failure and details.
    """
    url = config.get("url")
    if not url:
        return IntegrationTestResult(
            success=False,
            message="Webhook URL is required",
            error="Missing url",
        )

    method = config.get("method", "POST").upper()
    timeout = config.get("timeout", 10)
    headers = config.get("headers", {})
    headers.setdefault("Content-Type", "application/json")

    # Security: Validate timeout
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 60:
        timeout = 10

    # Create test payload
    test_payload = {"test": True, "event": "integration_test", "timestamp": "2024-01-01T00:00:00Z"}

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, json=test_payload, headers=headers)

            if response.status_code < 400:
                return IntegrationTestResult(
                    success=True,
                    message=f"Webhook connection test successful (status: {response.status_code})",
                    details={
                        "url": url,
                        "method": method,
                        "status_code": response.status_code,
                    },
                )
            else:
                return IntegrationTestResult(
                    success=False,
                    message=f"Webhook returned error status: {response.status_code}",
                    error=f"HTTP {response.status_code}",
                    details={
                        "url": url,
                        "method": method,
                        "status_code": response.status_code,
                    },
                )

    except httpx.TimeoutException:
        return IntegrationTestResult(
            success=False,
            message="Webhook connection timed out",
            error=f"Timeout after {timeout} seconds",
            details={"url": url, "timeout": timeout},
        )
    except httpx.ConnectError as e:
        return IntegrationTestResult(
            success=False,
            message="Failed to connect to webhook endpoint",
            error=f"Connection error: {str(e)}",
            details={"url": url},
        )
    except Exception as e:
        logger.error(f"Unexpected error during webhook test: {e}", exc_info=True)
        return IntegrationTestResult(
            success=False,
            message="Unexpected error during webhook connection test",
            error=f"Unexpected error: {str(e)}",
            details={"url": url},
        )


def test_oauth_integration(config: dict[str, Any]) -> IntegrationTestResult:
    """
    Test OAuth integration by validating token.

    Args:
        config: Dictionary containing OAuth configuration:
            - token: OAuth access token (required)
            - token_type: Token type (default: Bearer)
            - validation_url: URL to validate token (optional)
            - client_id: OAuth client ID (optional, for refresh test)
            - client_secret: OAuth client secret (optional, for refresh test)
            - refresh_token: Refresh token (optional, for refresh test)

    Returns:
        IntegrationTestResult indicating success or failure and details.
    """
    token = config.get("token")
    if not token:
        return IntegrationTestResult(
            success=False,
            message="OAuth token is required",
            error="Missing token",
        )

    token_type = config.get("token_type", "Bearer")
    validation_url = config.get("validation_url")

    # If validation URL is provided, validate token
    if validation_url:
        try:
            timeout = config.get("timeout", 10)
            headers = {"Authorization": f"{token_type} {token}"}

            with httpx.Client(timeout=timeout) as client:
                response = client.get(validation_url, headers=headers)

                if response.status_code == 200:
                    return IntegrationTestResult(
                        success=True,
                        message="OAuth token validation successful",
                        details={
                            "token_type": token_type,
                            "validation_url": validation_url,
                            "status_code": response.status_code,
                        },
                    )
                else:
                    return IntegrationTestResult(
                        success=False,
                        message=f"OAuth token validation failed (status: {response.status_code})",
                        error=f"HTTP {response.status_code}",
                        details={
                            "token_type": token_type,
                            "validation_url": validation_url,
                            "status_code": response.status_code,
                        },
                    )

        except Exception as e:
            logger.error(f"Error during OAuth token validation: {e}", exc_info=True)
            return IntegrationTestResult(
                success=False,
                message="OAuth token validation error",
                error=f"Validation error: {str(e)}",
                details={"token_type": token_type, "validation_url": validation_url},
            )

    # If no validation URL, just check token format
    # Basic validation: token should not be empty
    if len(token) < 10:  # Minimum reasonable token length
        return IntegrationTestResult(
            success=False,
            message="OAuth token appears to be invalid (too short)",
            error="Invalid token format",
            details={"token_type": token_type},
        )

    return IntegrationTestResult(
        success=True,
        message="OAuth token format appears valid (no validation URL provided)",
        details={"token_type": token_type},
    )


def test_database_integration(config: dict[str, Any]) -> IntegrationTestResult:
    """
    Test database integration by attempting connection.

    Args:
        config: Dictionary containing database configuration:
            - host: Database host (required)
            - port: Database port (required)
            - database: Database name (required)
            - username: Database username (required)
            - password: Database password (required)
            - db_type: Database type ('postgresql', 'mysql', 'mongodb', etc.)

    Returns:
        IntegrationTestResult indicating success or failure and details.
    """
    host = config.get("host")
    port = config.get("port")
    database = config.get("database")
    username = config.get("username")
    password = config.get("password")
    db_type = config.get("db_type", "postgresql").lower()

    if not all([host, port, database, username, password]):
        missing = [k for k, v in {"host": host, "port": port, "database": database, "username": username, "password": password}.items() if not v]
        return IntegrationTestResult(
            success=False,
            message=f"Database configuration incomplete. Missing: {', '.join(missing)}",
            error="Missing required fields",
        )

    try:
        if db_type == "postgresql":
            import psycopg2

            conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10,
            )
            conn.close()
            return IntegrationTestResult(
                success=True,
                message="PostgreSQL connection test successful",
                details={"host": host, "port": port, "database": database},
            )

        elif db_type == "mysql":
            import pymysql

            conn = pymysql.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=10,
            )
            conn.close()
            return IntegrationTestResult(
                success=True,
                message="MySQL connection test successful",
                details={"host": host, "port": port, "database": database},
            )

        else:
            return IntegrationTestResult(
                success=False,
                message=f"Unsupported database type: {db_type}",
                error="Unsupported db_type",
                details={"db_type": db_type},
            )

    except ImportError as e:
        return IntegrationTestResult(
            success=False,
            message=f"Database driver not installed: {str(e)}",
            error="Missing driver",
            details={"db_type": db_type},
        )
    except Exception as e:
        logger.error(f"Error during database connection test: {e}", exc_info=True)
        return IntegrationTestResult(
            success=False,
            message=f"Database connection failed: {str(e)}",
            error=f"Connection error: {str(e)}",
            details={"host": host, "port": port, "database": database, "db_type": db_type},
        )


def test_integration(integration_type: IntegrationType, config: dict[str, Any]) -> IntegrationTestResult:
    """
    Test an integration based on its type.

    Args:
        integration_type: Type of integration to test
        config: Integration configuration dictionary

    Returns:
        IntegrationTestResult indicating success or failure and details.
    """
    if integration_type == IntegrationType.WEBHOOK:
        return test_webhook_integration(config)

    elif integration_type in [IntegrationType.STRIPE, IntegrationType.TWILIO, IntegrationType.SLACK, IntegrationType.ZAPIER, IntegrationType.CUSTOM]:
        # These typically use REST API
        return test_rest_api_integration(config)

    elif integration_type == IntegrationType.GOOGLE_CALENDAR:
        # Google Calendar uses OAuth
        return test_oauth_integration(config)

    else:
        return IntegrationTestResult(
            success=False,
            message=f"Unsupported integration type: {integration_type}",
            error="Unsupported type",
            details={"type": integration_type.value},
        )






