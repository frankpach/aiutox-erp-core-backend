"""Unit tests for RefreshTokenRepository."""

from datetime import UTC, datetime, timedelta

from app.repositories.refresh_token_repository import RefreshTokenRepository


class TestRefreshTokenRepository:
    """Test suite for RefreshTokenRepository."""

    def test_create_refresh_token(self, db_session, test_user):
        """Test creating a refresh token."""
        repo = RefreshTokenRepository(db_session)
        token = "test_refresh_token_12345"
        expires_at = datetime.now(UTC) + timedelta(days=7)

        refresh_token = repo.create(
            user_id=test_user.id, token=token, expires_at=expires_at
        )

        assert refresh_token.id is not None
        assert refresh_token.user_id == test_user.id
        assert refresh_token.expires_at == expires_at
        assert refresh_token.token_hash is not None
        assert refresh_token.revoked_at is None

    def test_get_by_token_hash(self, db_session, test_user):
        """Test getting a refresh token by token hash."""
        repo = RefreshTokenRepository(db_session)
        from app.core.auth.token_hash import verify_token

        token = "test_refresh_token_12345"
        expires_at = datetime.now(UTC) + timedelta(days=7)

        created_token = repo.create(
            user_id=test_user.id, token=token, expires_at=expires_at
        )
        assert created_token.token_hash is not None
        assert verify_token(token, created_token.token_hash)

        found_token = repo.get_by_token_hash(created_token.token_hash)

        assert found_token is not None
        assert found_token.id == created_token.id
        assert found_token.user_id == test_user.id

    def test_get_by_token_hash_not_found(self, db_session):
        """Test getting a non-existent refresh token by hash."""
        repo = RefreshTokenRepository(db_session)
        from app.core.auth.token_hash import hash_token

        non_existent_hash = hash_token("non_existent_token")
        token = repo.get_by_token_hash(non_existent_hash)

        assert token is None

    def test_find_valid_token(self, db_session, test_user):
        """Test finding a valid refresh token for a user."""
        repo = RefreshTokenRepository(db_session)
        token = "test_refresh_token_12345"
        expires_at = datetime.now(UTC) + timedelta(days=7)

        created_token = repo.create(
            user_id=test_user.id, token=token, expires_at=expires_at
        )

        found_token = repo.find_valid_token(test_user.id, token)

        assert found_token is not None
        assert found_token.id == created_token.id

    def test_find_valid_token_wrong_token(self, db_session, test_user):
        """Test finding a token with wrong token string."""
        repo = RefreshTokenRepository(db_session)
        token = "test_refresh_token_12345"
        expires_at = datetime.now(UTC) + timedelta(days=7)

        repo.create(user_id=test_user.id, token=token, expires_at=expires_at)

        found_token = repo.find_valid_token(test_user.id, "wrong_token")

        assert found_token is None

    def test_find_valid_token_expired(self, db_session, test_user):
        """Test that expired tokens are not found."""
        repo = RefreshTokenRepository(db_session)
        token = "test_refresh_token_12345"
        expires_at = datetime.now(UTC) - timedelta(days=1)  # Expired

        repo.create(user_id=test_user.id, token=token, expires_at=expires_at)

        found_token = repo.find_valid_token(test_user.id, token)

        assert found_token is None

    def test_find_valid_token_revoked(self, db_session, test_user):
        """Test that revoked tokens are not found."""
        repo = RefreshTokenRepository(db_session)
        token = "test_refresh_token_12345"
        expires_at = datetime.now(UTC) + timedelta(days=7)

        created_token = repo.create(
            user_id=test_user.id, token=token, expires_at=expires_at
        )
        repo.revoke_token(created_token)

        found_token = repo.find_valid_token(test_user.id, token)

        assert found_token is None

    def test_revoke_token(self, db_session, test_user):
        """Test revoking a refresh token."""
        repo = RefreshTokenRepository(db_session)
        token = "test_refresh_token_12345"
        expires_at = datetime.now(UTC) + timedelta(days=7)

        refresh_token = repo.create(
            user_id=test_user.id, token=token, expires_at=expires_at
        )
        assert refresh_token.revoked_at is None

        repo.revoke_token(refresh_token)

        # Refresh from DB
        db_session.refresh(refresh_token)
        assert refresh_token.revoked_at is not None

    def test_revoke_all_user_tokens(self, db_session, test_user):
        """Test revoking all refresh tokens for a user."""
        repo = RefreshTokenRepository(db_session)

        # Create multiple tokens
        token1 = repo.create(
            user_id=test_user.id,
            token="token1",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        token2 = repo.create(
            user_id=test_user.id,
            token="token2",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        # Revoke all
        count = repo.revoke_all_user_tokens(test_user.id)

        assert count == 2

        # Verify tokens are revoked
        db_session.refresh(token1)
        db_session.refresh(token2)
        assert token1.revoked_at is not None
        assert token2.revoked_at is not None

    def test_revoke_all_user_tokens_none_exist(self, db_session, test_user):
        """Test revoking all tokens when user has none."""
        repo = RefreshTokenRepository(db_session)

        count = repo.revoke_all_user_tokens(test_user.id)

        assert count == 0

    def test_revoke_all_user_tokens_only_active(self, db_session, test_user):
        """Test that only active tokens are revoked."""
        repo = RefreshTokenRepository(db_session)

        # Create active token
        active_token = repo.create(
            user_id=test_user.id,
            token="active_token",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )

        # Create and revoke a token
        revoked_token = repo.create(
            user_id=test_user.id,
            token="revoked_token",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        repo.revoke_token(revoked_token)

        # Revoke all (should only revoke the active one)
        count = repo.revoke_all_user_tokens(test_user.id)

        assert count == 1

        # Verify active token is revoked
        db_session.refresh(active_token)
        assert active_token.revoked_at is not None

    def test_delete_expired_tokens(self, db_session, test_user):
        """Test deleting expired and revoked tokens."""
        repo = RefreshTokenRepository(db_session)

        # Create expired and revoked token
        expired_token = repo.create(
            user_id=test_user.id,
            token="expired_token",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        # Save token hash before revoking and deleting
        expired_token_hash = expired_token.token_hash
        repo.revoke_token(expired_token)

        # Create expired but not revoked token (should not be deleted)
        expired_not_revoked = repo.create(
            user_id=test_user.id,
            token="expired_not_revoked",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        expired_not_revoked_hash = expired_not_revoked.token_hash

        # Create active token (should not be deleted)
        active_token = repo.create(
            user_id=test_user.id,
            token="active_token",
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        active_token_hash = active_token.token_hash

        # Delete expired and revoked tokens
        count = repo.delete_expired_tokens()

        assert count >= 1

        # Verify expired and revoked token is deleted
        found_token = repo.get_by_token_hash(expired_token_hash)
        assert found_token is None

        # Verify expired but not revoked token still exists
        found_token = repo.get_by_token_hash(expired_not_revoked_hash)
        assert found_token is not None

        # Verify active token still exists
        found_token = repo.get_by_token_hash(active_token_hash)
        assert found_token is not None
