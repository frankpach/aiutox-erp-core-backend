"""Integration tests for authentication service."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.user_role import UserRole
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.auth_service import AuthService


def test_authenticate_user_success(db_session, test_user):
    """Test that authenticate_user returns User for successful authentication."""
    auth_service = AuthService(db_session)

    result = auth_service.authenticate_user(test_user.email, test_user._plain_password)

    assert result is not None
    assert result.id == test_user.id
    assert result.email == test_user.email
    assert result.is_active is True


def test_authenticate_user_invalid_password(db_session, test_user):
    """Test that authenticate_user returns None for invalid password."""
    auth_service = AuthService(db_session)

    result = auth_service.authenticate_user(test_user.email, "wrong_password")

    assert result is None


def test_authenticate_user_not_exists(db_session):
    """Test that authenticate_user returns None for non-existent user (doesn't reveal existence)."""
    auth_service = AuthService(db_session)

    # Use a non-existent email
    result = auth_service.authenticate_user("nonexistent@example.com", "any_password")

    assert result is None


def test_authenticate_user_inactive(db_session, test_user_inactive):
    """Test that authenticate_user returns None for inactive user."""
    auth_service = AuthService(db_session)

    result = auth_service.authenticate_user(
        test_user_inactive.email, test_user_inactive._plain_password
    )

    assert result is None


def test_create_access_token_for_user(db_session, test_user, test_tenant):
    """Test that create_access_token_for_user generates token with complete payload."""
    auth_service = AuthService(db_session)

    token = auth_service.create_access_token_for_user(test_user)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify payload
    from app.core.auth import decode_token

    decoded = decode_token(token)
    assert decoded is not None
    assert decoded["sub"] == str(test_user.id)
    assert decoded["tenant_id"] == str(test_user.tenant_id)
    assert "roles" in decoded
    assert "permissions" in decoded
    assert decoded["type"] == "access"


def test_create_refresh_token_for_user(db_session, test_user):
    """Test that create_refresh_token_for_user creates and stores refresh token."""
    auth_service = AuthService(db_session)

    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    assert refresh_token is not None
    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0

    # Verify token is stored in database
    refresh_token_repo = RefreshTokenRepository(db_session)
    stored_token = refresh_token_repo.find_valid_token(test_user.id, refresh_token)
    assert stored_token is not None
    assert stored_token.user_id == test_user.id


def test_refresh_access_token_valid(db_session, test_user):
    """Test that refresh_access_token generates new access token for valid refresh token."""
    auth_service = AuthService(db_session)

    # Create refresh token
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Refresh access token
    result = auth_service.refresh_access_token(refresh_token)

    assert result is not None
    new_access_token, new_refresh_token, refresh_expires_at = result
    assert isinstance(new_access_token, str)
    assert len(new_access_token) > 0
    assert isinstance(new_refresh_token, str)
    assert len(new_refresh_token) > 0
    assert refresh_expires_at is not None

    # Verify new token is valid
    from app.core.auth import decode_token

    decoded = decode_token(new_access_token)
    assert decoded is not None
    assert decoded["sub"] == str(test_user.id)
    assert decoded["type"] == "access"

    # Old refresh token should be revoked, new one should be valid
    refresh_token_repo = RefreshTokenRepository(db_session)
    assert refresh_token_repo.find_valid_token(test_user.id, refresh_token) is None
    assert (
        refresh_token_repo.find_valid_token(test_user.id, new_refresh_token) is not None
    )


def test_refresh_access_token_expired(db_session, test_user):
    """Test that refresh_access_token returns None for expired refresh token."""
    auth_service = AuthService(db_session)

    # Create refresh token with very short expiration
    from app.core.auth import create_refresh_token
    from app.repositories.refresh_token_repository import RefreshTokenRepository

    refresh_token_str = create_refresh_token(test_user.id)
    expires_at = datetime.now(UTC) + timedelta(seconds=-1)  # Expired

    refresh_token_repo = RefreshTokenRepository(db_session)
    refresh_token_repo.create(test_user.id, refresh_token_str, expires_at)

    # Wait a bit to ensure expiration
    import time

    time.sleep(2)

    # Try to refresh
    result = auth_service.refresh_access_token(refresh_token_str)

    assert result is None


def test_refresh_access_token_revoked(db_session, test_user):
    """Test that refresh_access_token returns None for revoked refresh token."""
    auth_service = AuthService(db_session)

    # Create refresh token
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Revoke token
    auth_service.revoke_refresh_token(refresh_token, test_user.id)

    # Try to refresh
    result = auth_service.refresh_access_token(refresh_token)

    assert result is None


def test_revoke_refresh_token(db_session, test_user):
    """Test that revoke_refresh_token revokes token correctly."""
    auth_service = AuthService(db_session)

    # Create refresh token
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Revoke token
    result = auth_service.revoke_refresh_token(refresh_token, test_user.id)

    assert result is True

    # Verify token is revoked
    refresh_token_repo = RefreshTokenRepository(db_session)
    stored_token = refresh_token_repo.find_valid_token(test_user.id, refresh_token)
    assert stored_token is None


def test_get_user_roles(db_session, test_user):
    """Test that get_user_roles returns user's roles."""
    auth_service = AuthService(db_session)

    # Assign role
    role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    roles = auth_service.get_user_roles(test_user.id)

    assert "admin" in roles
    assert len(roles) == 1


def test_get_user_permissions(db_session, test_user):
    """Test that get_user_permissions returns user's permissions (Phase 1: empty list)."""
    auth_service = AuthService(db_session)

    permissions = auth_service.get_user_permissions(test_user.id)

    # Phase 1: Returns empty list (will be implemented in Phase 2)
    assert isinstance(permissions, list)
    assert len(permissions) == 0


def test_revoke_all_user_tokens(db_session, test_user):
    """Test that revoke_all_user_tokens revokes all tokens for a user."""
    auth_service = AuthService(db_session)

    # Create multiple refresh tokens
    token1 = auth_service.create_refresh_token_for_user(test_user)
    token2 = auth_service.create_refresh_token_for_user(test_user)

    # Revoke all tokens
    count = auth_service.revoke_all_user_tokens(test_user.id)

    assert count >= 2

    # Verify all tokens are revoked
    refresh_token_repo = RefreshTokenRepository(db_session)
    stored_token1 = refresh_token_repo.find_valid_token(test_user.id, token1)
    stored_token2 = refresh_token_repo.find_valid_token(test_user.id, token2)

    assert stored_token1 is None
    assert stored_token2 is None


def test_refresh_token_user_deleted_after_creation(db_session, test_user):
    """Test that refresh fails if user is deleted after token creation."""
    auth_service = AuthService(db_session)
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Delete user
    db_session.delete(test_user)
    db_session.commit()

    # Try to refresh
    result = auth_service.refresh_access_token(refresh_token)

    assert result is None


def test_get_user_roles_multiple_roles(db_session, test_user):
    """Test that get_user_roles returns all roles for a user."""
    auth_service = AuthService(db_session)

    # Assign multiple roles
    role1 = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    role2 = UserRole(
        user_id=test_user.id,
        role="manager",
        granted_by=test_user.id,
    )
    db_session.add(role1)
    db_session.add(role2)
    db_session.commit()

    roles = auth_service.get_user_roles(test_user.id)

    assert "admin" in roles
    assert "manager" in roles
    assert len(roles) == 2


def test_get_user_roles_no_roles(db_session, test_user):
    """Test that get_user_roles returns empty list for user with no roles."""
    auth_service = AuthService(db_session)

    roles = auth_service.get_user_roles(test_user.id)

    assert isinstance(roles, list)
    assert len(roles) == 0


def test_create_access_token_for_user_includes_roles(db_session, test_user):
    """Test that create_access_token_for_user includes user roles in token."""
    auth_service = AuthService(db_session)

    # Assign role
    role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.commit()

    token = auth_service.create_access_token_for_user(test_user)

    # Decode and verify roles
    from app.core.auth import decode_token

    decoded = decode_token(token)
    assert decoded is not None
    assert "roles" in decoded
    assert "admin" in decoded["roles"]


def test_revoke_refresh_token_invalid_user_id(db_session, test_user):
    """Test that revoke_refresh_token returns False for invalid user_id."""
    auth_service = AuthService(db_session)
    refresh_token = auth_service.create_refresh_token_for_user(test_user)

    # Try to revoke with wrong user_id

    wrong_user_id = uuid4()
    result = auth_service.revoke_refresh_token(refresh_token, wrong_user_id)

    assert result is False

    # Verify token is still valid
    refresh_token_repo = RefreshTokenRepository(db_session)
    stored_token = refresh_token_repo.find_valid_token(test_user.id, refresh_token)
    assert stored_token is not None
