"""Unit tests for integration testing functionality."""

from unittest.mock import MagicMock, Mock, patch

import httpx

# Import module to avoid pytest detecting functions as tests
from app.core.integrations import integration_test
from app.core.integrations.integration_test import IntegrationTestResult
from app.models.integration import IntegrationType


class TestRESTAPIIntegration:
    """Test suite for REST API integration testing."""

    def test_rest_api_success(self):
        """Test successful REST API connection."""
        config = {
            "url": "https://api.example.com/test",
            "method": "GET",
            "auth_type": "bearer",
            "auth_token": "test_token",
        }

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"OK"
            mock_response.text = "OK"

            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.request = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = integration_test.test_rest_api_integration(config)

            assert result.success is True
            assert "successful" in result.message.lower()
            assert result.error is None
            assert result.details["status_code"] == 200

    def test_rest_api_missing_url(self):
        """Test REST API with missing URL."""
        config = {"method": "GET"}

        result = integration_test.test_rest_api_integration(config)

        assert result.success is False
        assert "url" in result.message.lower() or "required" in result.message.lower()

    def test_rest_api_timeout(self):
        """Test REST API connection timeout."""
        config = {"url": "https://api.example.com/test", "timeout": 5}

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.request = Mock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            result = integration_test.test_rest_api_integration(config)

            assert result.success is False
            assert "timeout" in result.message.lower() or "timed out" in result.message.lower()

    def test_rest_api_connection_error(self):
        """Test REST API connection error."""
        config = {"url": "https://invalid.example.com/test"}

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.request = Mock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client_class.return_value = mock_client

            result = integration_test.test_rest_api_integration(config)

            assert result.success is False
            assert "connection" in result.message.lower() or "connect" in result.message.lower()

    def test_rest_api_error_status(self):
        """Test REST API with error status code."""
        config = {"url": "https://api.example.com/test"}

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.request = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = integration_test.test_rest_api_integration(config)

            assert result.success is False
            assert "error" in result.message.lower() or "401" in result.message


class TestWebhookIntegration:
    """Test suite for webhook integration testing."""

    def test_webhook_success(self):
        """Test successful webhook connection."""
        config = {"url": "https://webhook.example.com/test", "method": "POST"}

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200

            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.request = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = integration_test.test_webhook_integration(config)

            assert result.success is True
            assert "successful" in result.message.lower()

    def test_webhook_missing_url(self):
        """Test webhook with missing URL."""
        config = {"method": "POST"}

        result = integration_test.test_webhook_integration(config)

        assert result.success is False
        assert "url" in result.message.lower() or "required" in result.message.lower()

    def test_webhook_timeout(self):
        """Test webhook connection timeout."""
        config = {"url": "https://webhook.example.com/test", "timeout": 5}

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.request = Mock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client_class.return_value = mock_client

            result = integration_test.test_webhook_integration(config)

            assert result.success is False
            assert "timeout" in result.message.lower() or "timed out" in result.message.lower()


class TestOAuthIntegration:
    """Test suite for OAuth integration testing."""

    def test_oauth_success_with_validation(self):
        """Test successful OAuth token validation."""
        config = {
            "token": "valid_oauth_token_12345",
            "token_type": "Bearer",
            "validation_url": "https://api.example.com/validate",
        }

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 200

            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.get = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = integration_test.test_oauth_integration(config)

            assert result.success is True
            assert "successful" in result.message.lower()

    def test_oauth_success_without_validation(self):
        """Test OAuth token format validation without validation URL."""
        config = {"token": "valid_oauth_token_12345", "token_type": "Bearer"}

        result = integration_test.test_oauth_integration(config)

        assert result.success is True
        assert "format" in result.message.lower() or "valid" in result.message.lower()

    def test_oauth_missing_token(self):
        """Test OAuth with missing token."""
        config = {"token_type": "Bearer"}

        result = integration_test.test_oauth_integration(config)

        assert result.success is False
        assert "token" in result.message.lower() or "required" in result.message.lower()

    def test_oauth_invalid_token_format(self):
        """Test OAuth with invalid token format (too short)."""
        config = {"token": "short"}

        result = integration_test.test_oauth_integration(config)

        assert result.success is False
        assert "invalid" in result.message.lower() or "short" in result.message.lower()

    def test_oauth_validation_failed(self):
        """Test OAuth token validation failure."""
        config = {
            "token": "invalid_token",
            "token_type": "Bearer",
            "validation_url": "https://api.example.com/validate",
        }

        with patch("app.core.integrations.integration_test.httpx.Client") as mock_client_class:
            mock_response = Mock()
            mock_response.status_code = 401

            mock_client = MagicMock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.get = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = integration_test.test_oauth_integration(config)

            assert result.success is False
            assert "failed" in result.message.lower() or "401" in result.message


class TestDatabaseIntegration:
    """Test suite for database integration testing."""

    @patch("psycopg2.connect")
    def test_postgresql_success(self, mock_connect):
        """Test successful PostgreSQL connection."""
        config = {
            "host": "localhost",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass",
            "db_type": "postgresql",
        }

        mock_conn = Mock()
        mock_conn.close = Mock()
        mock_connect.return_value = mock_conn

        result = integration_test.test_database_integration(config)

        assert result.success is True
        assert "postgresql" in result.message.lower() or "successful" in result.message.lower()
        mock_connect.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_database_missing_fields(self):
        """Test database connection with missing required fields."""
        config = {"host": "localhost", "port": 5432}  # Missing database, username, password

        result = integration_test.test_database_integration(config)

        assert result.success is False
        assert "missing" in result.message.lower() or "incomplete" in result.message.lower()

    @patch("psycopg2.connect")
    def test_postgresql_connection_error(self, mock_connect):
        """Test PostgreSQL connection error."""
        config = {
            "host": "invalid_host",
            "port": 5432,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass",
            "db_type": "postgresql",
        }

        mock_connect.side_effect = Exception("Connection refused")

        result = integration_test.test_database_integration(config)

        assert result.success is False
        assert "failed" in result.message.lower() or "error" in result.message.lower()

    def test_database_unsupported_type(self):
        """Test database with unsupported type."""
        config = {
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass",
            "db_type": "oracle",  # Unsupported
        }

        result = integration_test.test_database_integration(config)

        assert result.success is False
        assert "unsupported" in result.message.lower()


class TestIntegrationTest:
    """Test suite for main test_integration function."""

    def test_webhook_type(self):
        """Test webhook integration type."""
        config = {"url": "https://webhook.example.com/test"}

        with patch("app.core.integrations.integration_test.test_webhook_integration") as mock_test:
            mock_test.return_value = IntegrationTestResult(
                success=True, message="Test successful"
            )

            result = integration_test.test_integration(IntegrationType.WEBHOOK, config)

            assert result.success is True
            mock_test.assert_called_once_with(config)

    def test_rest_api_types(self):
        """Test REST API integration types (Stripe, Twilio, etc.)."""
        config = {"url": "https://api.example.com/test"}

        for integration_type in [
            IntegrationType.STRIPE,
            IntegrationType.TWILIO,
            IntegrationType.SLACK,
            IntegrationType.ZAPIER,
            IntegrationType.CUSTOM,
        ]:
            with patch("app.core.integrations.integration_test.test_rest_api_integration") as mock_test:
                mock_test.return_value = IntegrationTestResult(
                    success=True, message="Test successful"
                )

                result = integration_test.test_integration(integration_type, config)

                assert result.success is True
                mock_test.assert_called_once_with(config)

    def test_oauth_type(self):
        """Test OAuth integration type (Google Calendar)."""
        config = {"token": "test_token"}

        with patch("app.core.integrations.integration_test.test_oauth_integration") as mock_test:
            mock_test.return_value = IntegrationTestResult(
                success=True, message="Test successful"
            )

            result = integration_test.test_integration(IntegrationType.GOOGLE_CALENDAR, config)

            assert result.success is True
            mock_test.assert_called_once_with(config)

