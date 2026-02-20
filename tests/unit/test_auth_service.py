"""Unit tests for AuthService."""

from unittest.mock import Mock, patch

from app.services.auth_service import AuthService


class TestAuthService:
    """Test suite for AuthService."""

    def test_authenticate_user_success(self, db_session, test_user):
        """Test authenticating a user with correct credentials."""
        service = AuthService(db_session)

        plain_password = getattr(test_user, "_plain_password", "test_password_123")
        service.user_repository.get_by_email = Mock(return_value=test_user)
        service.user_repository.verify_password = Mock(return_value=True)

        result = service.authenticate_user(test_user.email, plain_password)

        assert result is not None
        assert result.id == test_user.id
        service.user_repository.get_by_email.assert_called_once_with(test_user.email)
        service.user_repository.verify_password.assert_called_once_with(
            test_user, plain_password
        )

    def test_authenticate_user_invalid_password(self, db_session, test_user):
        """Test authenticating with invalid password."""
        service = AuthService(db_session)

        service.user_repository.get_by_email = Mock(return_value=test_user)
        service.user_repository.verify_password = Mock(return_value=False)

        result = service.authenticate_user(test_user.email, "wrong_password")

        assert result is None

    def test_authenticate_user_not_found(self, db_session):
        """Test authenticating a non-existent user (timing attack protection)."""
        service = AuthService(db_session)

        service.user_repository.get_by_email = Mock(return_value=None)

        with patch("app.services.auth_service.verify_password") as mock_verify:
            result = service.authenticate_user("nonexistent@example.com", "password")

            assert result is None
            # Verify dummy password check was performed
            mock_verify.assert_called_once()

    def test_authenticate_user_inactive(self, db_session, test_user):
        """Test authenticating an inactive user."""
        service = AuthService(db_session)

        test_user.is_active = False
        service.user_repository.get_by_email = Mock(return_value=test_user)

        result = service.authenticate_user(test_user.email, "password")

        assert result is None

    def test_create_access_token_for_user(self, db_session, test_user):
        """Test creating an access token for a user."""
        service = AuthService(db_session)

        with patch.object(service, "get_user_roles", return_value=["admin"]):
            with patch.object(
                service, "get_user_permissions", return_value=["auth.manage_users"]
            ):
                with patch(
                    "app.services.auth_service.create_access_token"
                ) as mock_create:
                    mock_create.return_value = "test_access_token"

                    token = service.create_access_token_for_user(test_user)

                    assert token == "test_access_token"
                    mock_create.assert_called_once()
                    call_args = mock_create.call_args[0][0]
                    assert call_args["sub"] == str(test_user.id)
                    assert call_args["tenant_id"] == str(test_user.tenant_id)
                    assert "admin" in call_args["roles"]

    def test_create_refresh_token_for_user(self, db_session, test_user):
        """Test creating a refresh token for a user."""
        service = AuthService(db_session)

        with patch("app.services.auth_service.create_refresh_token") as mock_create:
            with patch.object(
                service.refresh_token_repository, "create"
            ) as mock_repo_create:
                mock_create.return_value = "test_refresh_token"

                token = service.create_refresh_token_for_user(test_user)

                assert token == "test_refresh_token"
                mock_create.assert_called_once_with(test_user.id, False)
                mock_repo_create.assert_called_once()

    def test_refresh_access_token_success(self, db_session, test_user):
        """Test refreshing an access token with valid refresh token."""
        service = AuthService(db_session)

        refresh_token = "valid_refresh_token"
        payload = {"sub": str(test_user.id), "exp": 4102444800}

        with patch(
            "app.services.auth_service.verify_refresh_token", return_value=payload
        ):
            mock_stored_token = Mock()
            service.refresh_token_repository.find_valid_token = Mock(
                return_value=mock_stored_token
            )
            service.refresh_token_repository.create = Mock()
            service.refresh_token_repository.revoke_token = Mock()
            service.user_repository.get_by_id = Mock(return_value=test_user)

            with (
                patch.object(
                    service, "create_access_token_for_user"
                ) as mock_create_token,
                patch(
                    "app.services.auth_service.create_refresh_token"
                ) as mock_create_refresh,
            ):
                mock_create_token.return_value = "new_access_token"
                mock_create_refresh.return_value = "new_refresh_token"

                result = service.refresh_access_token(refresh_token)

                assert result is not None
                access_token, new_refresh_token, refresh_expires_at = result
                assert access_token == "new_access_token"
                assert new_refresh_token == "new_refresh_token"
                assert refresh_expires_at is not None
                service.refresh_token_repository.create.assert_called_once()
                service.refresh_token_repository.revoke_token.assert_called_once_with(
                    mock_stored_token
                )
                service.refresh_token_repository.find_valid_token.assert_called_once_with(
                    test_user.id, refresh_token
                )

    def test_refresh_access_token_invalid(self, db_session):
        """Test refreshing with invalid refresh token."""
        service = AuthService(db_session)

        with patch("app.services.auth_service.verify_refresh_token", return_value=None):
            with patch(
                "app.services.auth_service.log_refresh_token_invalid"
            ) as mock_log:
                result = service.refresh_access_token("invalid_token")

                assert result is None
                mock_log.assert_called_once()

    def test_refresh_access_token_not_found(self, db_session, test_user):
        """Test refreshing with token not found in database."""
        service = AuthService(db_session)

        refresh_token = "valid_but_not_stored_token"
        payload = {"sub": str(test_user.id), "exp": 4102444800}

        with patch(
            "app.services.auth_service.verify_refresh_token", return_value=payload
        ):
            service.refresh_token_repository.find_valid_token = Mock(return_value=None)

            with patch(
                "app.services.auth_service.log_refresh_token_invalid"
            ) as mock_log:
                result = service.refresh_access_token(refresh_token)

                assert result is None
                mock_log.assert_called_once()

    def test_revoke_refresh_token_success(self, db_session, test_user):
        """Test revoking a refresh token successfully."""
        service = AuthService(db_session)

        refresh_token = "token_to_revoke"
        mock_stored_token = Mock()

        service.refresh_token_repository.find_valid_token = Mock(
            return_value=mock_stored_token
        )
        service.refresh_token_repository.revoke_token = Mock()

        result = service.revoke_refresh_token(refresh_token, test_user.id)

        assert result is True
        service.refresh_token_repository.find_valid_token.assert_called_once_with(
            test_user.id, refresh_token
        )
        service.refresh_token_repository.revoke_token.assert_called_once_with(
            mock_stored_token
        )

    def test_revoke_refresh_token_not_found(self, db_session, test_user):
        """Test revoking a non-existent refresh token."""
        service = AuthService(db_session)

        service.refresh_token_repository.find_valid_token = Mock(return_value=None)

        result = service.revoke_refresh_token("nonexistent_token", test_user.id)

        assert result is False

    def test_revoke_all_user_tokens(self, db_session, test_user):
        """Test revoking all refresh tokens for a user."""
        service = AuthService(db_session)

        service.refresh_token_repository.revoke_all_user_tokens = Mock(return_value=3)

        count = service.revoke_all_user_tokens(test_user.id)

        assert count == 3
        service.refresh_token_repository.revoke_all_user_tokens.assert_called_once_with(
            test_user.id
        )
