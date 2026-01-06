"""Unit tests for SMTP connection testing functionality."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from smtplib import SMTPAuthenticationError, SMTPConnectError, SMTPServerDisconnected

from app.core.notifications.smtp_test import (
    SMTPTestResult,
    check_smtp_connection,
)


class TestSMTPConnection:
    """Test suite for SMTP connection testing."""

    def test_smtp_connection_success(self):
        """Test successful SMTP connection."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "user": "user@example.com",
            "password": "password123",
            "use_tls": True,
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_instance = MagicMock()
            mock_smtp_instance.__enter__ = Mock(return_value=mock_server)
            mock_smtp_instance.__exit__ = Mock(return_value=None)
            mock_smtp_class.return_value = mock_smtp_instance

            result = check_smtp_connection(config)

            assert result.success is True
            assert "successful" in result.message.lower()
            assert result.error is None
            mock_smtp_class.assert_called_once_with("smtp.example.com", 587, timeout=10)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user@example.com", "password123")

    def test_smtp_connection_without_tls(self):
        """Test SMTP connection without TLS."""
        config = {
            "host": "smtp.example.com",
            "port": 25,
            "user": "user@example.com",
            "password": "password123",
            "use_tls": False,
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_instance = MagicMock()
            mock_smtp_instance.__enter__ = Mock(return_value=mock_server)
            mock_smtp_instance.__exit__ = Mock(return_value=None)
            mock_smtp_class.return_value = mock_smtp_instance

            result = check_smtp_connection(config)

            assert result.success is True
            mock_server.starttls.assert_not_called()
            mock_server.login.assert_called_once()

    def test_smtp_connection_authentication_error(self):
        """Test SMTP connection with authentication error."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "user": "user@example.com",
            "password": "wrongpassword",
            "use_tls": True,
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_instance = MagicMock()
            mock_smtp_instance.__enter__ = Mock(return_value=mock_server)
            mock_smtp_instance.__exit__ = Mock(return_value=None)
            mock_smtp_class.return_value = mock_smtp_instance
            mock_server.starttls.return_value = None
            mock_server.login.side_effect = SMTPAuthenticationError(535, b"Authentication failed")

            result = check_smtp_connection(config)

            assert result.success is False
            assert "authentication" in result.message.lower() or "auth" in result.message.lower()
            assert result.error is not None
            assert "535" in result.error or "authentication" in result.error.lower()

    def test_smtp_connection_connect_error(self):
        """Test SMTP connection with connection error."""
        config = {
            "host": "invalid.host.com",
            "port": 587,
            "user": "user@example.com",
            "password": "password123",
            "use_tls": True,
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_smtp_class.side_effect = SMTPConnectError(421, b"Connection refused")

            result = check_smtp_connection(config)

            assert result.success is False
            assert "connection" in result.message.lower() or "connect" in result.message.lower()
            assert result.error is not None
            assert "421" in result.error or "refused" in result.error.lower()

    def test_smtp_connection_timeout(self):
        """Test SMTP connection timeout."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "user": "user@example.com",
            "password": "password123",
            "use_tls": True,
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_smtp_class.side_effect = TimeoutError("Connection timed out")

            result = check_smtp_connection(config)

            assert result.success is False
            assert "timeout" in result.message.lower() or "timed out" in result.message.lower()
            assert result.error is not None

    def test_smtp_connection_server_disconnected(self):
        """Test SMTP connection with server disconnection."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "user": "user@example.com",
            "password": "password123",
            "use_tls": True,
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_instance = MagicMock()
            mock_smtp_instance.__enter__ = Mock(return_value=mock_server)
            mock_smtp_instance.__exit__ = Mock(return_value=None)
            mock_smtp_class.return_value = mock_smtp_instance
            mock_server.starttls.side_effect = SMTPServerDisconnected("Server disconnected")

            result = check_smtp_connection(config)

            assert result.success is False
            assert "disconnected" in result.message.lower() or "connection" in result.message.lower()
            assert result.error is not None

    def test_smtp_connection_missing_required_fields(self):
        """Test SMTP connection with missing required fields."""
        # Test missing host
        config_no_host = {
            "port": 587,
            "use_tls": True,
        }

        result = check_smtp_connection(config_no_host)

        assert result.success is False
        assert "required" in result.message.lower() or "host" in result.message.lower()

        # Test missing port
        config_no_port = {
            "host": "smtp.example.com",
            "use_tls": True,
        }

        result = check_smtp_connection(config_no_port)

        assert result.success is False
        assert "port" in result.message.lower()

    def test_smtp_connection_invalid_port(self):
        """Test SMTP connection with invalid port."""
        config = {
            "host": "smtp.example.com",
            "port": 99999,  # Invalid port
            "user": "user@example.com",
            "password": "password123",
            "use_tls": True,
        }

        result = check_smtp_connection(config)

        assert result.success is False
        assert "port" in result.message.lower() or "65535" in result.message
        assert result.error is not None

    def test_smtp_connection_generic_exception(self):
        """Test SMTP connection with generic exception."""
        config = {
            "host": "smtp.example.com",
            "port": 587,
            "user": "user@example.com",
            "password": "password123",
            "use_tls": True,
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_smtp_class.side_effect = Exception("Unexpected error")

            result = check_smtp_connection(config)

            assert result.success is False
            assert result.error is not None

    def test_smtp_connection_without_user_password(self):
        """Test SMTP connection without authentication (open relay)."""
        config = {
            "host": "smtp.example.com",
            "port": 25,
            "use_tls": False,
            # No user/password - open relay
        }

        with patch("app.core.notifications.smtp_test.SMTP") as mock_smtp_class:
            mock_server = Mock()
            mock_smtp_instance = MagicMock()
            mock_smtp_instance.__enter__ = Mock(return_value=mock_server)
            mock_smtp_instance.__exit__ = Mock(return_value=None)
            mock_smtp_class.return_value = mock_smtp_instance

            result = check_smtp_connection(config)

            # Should succeed if server allows open relay
            assert result.success is True
            mock_server.login.assert_not_called()

