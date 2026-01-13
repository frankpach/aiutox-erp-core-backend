"""Authentication service for login, token management, and user authentication."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.core.config_file import get_settings
from app.core.logging import (
    log_refresh_token_invalid,
    log_refresh_token_used,
)
from app.core.cache import cache_service
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository

settings = get_settings()


class AuthService:
    """Service for authentication business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.user_repository = UserRepository(db)
        self.refresh_token_repository = RefreshTokenRepository(db)
        self.db = db

    def authenticate_user(self, email: str, password: str) -> User | None:
        """
        Authenticate a user with email and password.

        Security: Does not reveal if the user exists.
        Returns None for both invalid credentials and non-existent users.

        Args:
            email: User email address.
            password: Plain text password.

        Returns:
            User object if authentication succeeds, None otherwise.
        """
        import logging
        logger = logging.getLogger("app")
        logger.debug(f"[AUTH] Step 1: Getting user by email={email}")

        user = self.user_repository.get_by_email(email)
        logger.debug(f"[AUTH] Step 1: User found={user is not None}")

        # Always perform password verification to prevent timing attacks
        # If user doesn't exist, verify against a dummy hash
        if user:
            logger.debug(f"[AUTH] Step 2: User exists, checking if active")
            if not user.is_active:
                logger.debug(f"[AUTH] Step 2: User is not active")
                return None
            logger.debug(f"[AUTH] Step 3: User is active, verifying password")
            if self.user_repository.verify_password(user, password):
                logger.debug(f"[AUTH] Step 3: Password verified successfully")
                return user
            logger.debug(f"[AUTH] Step 3: Password verification failed")
        else:
            logger.debug(f"[AUTH] Step 4: User does not exist, performing dummy verification")
            # Dummy verification to prevent timing attacks
            # This ensures similar response time whether user exists or not
            verify_password(password, hash_password("dummy"))
            logger.debug(f"[AUTH] Step 4: Dummy verification completed")

        logger.debug(f"[AUTH] Step 5: Returning None (authentication failed)")
        return None

    def get_user_permissions(self, user_id: UUID) -> list[str]:
        """
        Get effective permissions for a user.

        Phase 2: Only global roles are considered.
        Phase 3+: Will include module roles and delegated permissions.

        Args:
            user_id: User UUID.

        Returns:
            List of permission strings.
        """
        # Try cache first
        cached_permissions = cache_service.get_user_permissions(user_id)
        if cached_permissions is not None:
            return cached_permissions

        # Cache miss, query database
        from app.services.permission_service import PermissionService

        permission_service = PermissionService(self.db)
        permissions = permission_service.get_effective_permissions(user_id)
        permission_list = list(permissions)

        # Store in cache
        cache_service.set_user_permissions(user_id, permission_list)

        return permission_list

    def get_user_roles(self, user_id: UUID) -> list[str]:
        """
        Get global roles for a user.

        Args:
            user_id: User UUID.

        Returns:
            List of role strings (e.g., ["admin", "manager"]).
        """
        # Try cache first
        cached_roles = cache_service.get_user_roles(user_id)
        if cached_roles is not None:
            return cached_roles

        # Cache miss, query database
        from app.models.user_role import UserRole

        roles = (
            self.db.query(UserRole)
            .filter(UserRole.user_id == user_id)
            .all()
        )
        role_list = [role.role for role in roles]

        # Store in cache
        cache_service.set_user_roles(user_id, role_list)

        return role_list

    def create_access_token_for_user(self, user: User) -> str:
        """
        Create an access token for a user with roles and permissions.

        Args:
            user: User object.

        Returns:
            JWT access token string.
        """
        roles = self.get_user_roles(user.id)
        permissions = self.get_user_permissions(user.id)

        token_data = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "roles": roles,
            "permissions": permissions,
        }
        return create_access_token(token_data)

    def create_refresh_token_for_user(self, user: User, remember_me: bool = False) -> str:
        """
        Create a refresh token for a user and store it in the database.

        Args:
            user: User object.
            remember_me: If True, token expires in REFRESH_TOKEN_REMEMBER_ME_DAYS, otherwise REFRESH_TOKEN_EXPIRE_DAYS.

        Returns:
            JWT refresh token string (plain text, to be sent to client).
        """
        # Generate refresh token
        refresh_token = create_refresh_token(user.id, remember_me)

        # Calculate expiration
        expire_days = settings.REFRESH_TOKEN_REMEMBER_ME_DAYS if remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
        expires_at = datetime.now(timezone.utc) + timedelta(days=expire_days)

        # Store hashed token in database
        self.refresh_token_repository.create(user.id, refresh_token, expires_at)

        return refresh_token

    def refresh_access_token(
        self, refresh_token: str
    ) -> tuple[str, str, datetime] | None:
        """
        Refresh an access token using a valid refresh token.

        Args:
            refresh_token: Refresh token string.

        Returns:
            Tuple of (new access token, new refresh token, refresh token expiry) if valid, None otherwise.
        """
        # Verify refresh token signature and expiration
        payload = verify_refresh_token(refresh_token)
        if not payload:
            log_refresh_token_invalid("invalid_signature_or_expired")
            return None

        user_id = UUID(payload["sub"])
        refresh_exp = payload.get("exp")
        if not isinstance(refresh_exp, (int, float)):
            log_refresh_token_invalid("missing_exp")
            return None
        refresh_expires_at = datetime.fromtimestamp(refresh_exp, tz=timezone.utc)

        # Verify token exists in database and is not revoked
        stored_token = self.refresh_token_repository.find_valid_token(
            user_id, refresh_token
        )
        if not stored_token:
            log_refresh_token_invalid("token_not_found_or_revoked")
            return None

        # Get user and verify is active
        user = self.user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            log_refresh_token_invalid("user_not_found_or_inactive")
            return None

        # Log successful refresh token usage
        log_refresh_token_used(str(user_id))

        # Rotate refresh token (reuse original expiry)
        new_refresh_token = create_refresh_token(
            user_id, expires_at=refresh_expires_at
        )
        self.refresh_token_repository.create(user_id, new_refresh_token, refresh_expires_at)
        self.refresh_token_repository.revoke_token(stored_token)

        # Generate new access token
        access_token = self.create_access_token_for_user(user)
        return access_token, new_refresh_token, refresh_expires_at

    def revoke_refresh_token(self, refresh_token: str, user_id: UUID) -> bool:
        """
        Revoke a refresh token.

        Args:
            refresh_token: Refresh token string to revoke.
            user_id: User ID for validation.

        Returns:
            True if token was revoked, False otherwise.
        """
        stored_token = self.refresh_token_repository.find_valid_token(
            user_id, refresh_token
        )
        if not stored_token:
            return False

        self.refresh_token_repository.revoke_token(stored_token)
        return True

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """
        Revoke all refresh tokens for a user (logout from all devices).

        Args:
            user_id: User UUID.

        Returns:
            Number of tokens revoked.
        """
        return self.refresh_token_repository.revoke_all_user_tokens(user_id)
