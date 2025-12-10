"""Refresh token repository for data access operations."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.auth.token_hash import hash_token, verify_token
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """Repository for refresh token data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(
        self, user_id: UUID, token: str, expires_at: datetime
    ) -> RefreshToken:
        """Create a new refresh token with hashed token."""
        token_hash = hash_token(token)  # Using SHA256 + bcrypt for tokens > 72 bytes
        refresh_token = RefreshToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)
        return refresh_token

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Get refresh token by token hash."""
        return (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

    def find_valid_token(self, user_id: UUID, token: str) -> RefreshToken | None:
        """
        Find a valid refresh token for a user by verifying the token against stored hashes.

        Note: This is less efficient but necessary since we hash tokens.
        In production, consider using a faster hash algorithm or storing tokens differently.
        """
        now = datetime.now(timezone.utc)
        tokens = (
            self.db.query(RefreshToken)
            .filter(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > now,
                )
            )
            .all()
        )

        for stored_token in tokens:
            if verify_token(token, stored_token.token_hash):
                return stored_token
        return None

    def revoke_token(self, token: RefreshToken) -> None:
        """Revoke a refresh token by setting revoked_at."""
        token.revoked_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(token)

    def revoke_all_user_tokens(self, user_id: UUID) -> int:
        """Revoke all refresh tokens for a user."""
        now = datetime.now(timezone.utc)
        count = (
            self.db.query(RefreshToken)
            .filter(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None),
                )
            )
            .update({"revoked_at": now})
        )
        self.db.commit()
        return count

    def delete_expired_tokens(self) -> int:
        """Delete expired and revoked tokens (cleanup operation)."""
        now = datetime.now(timezone.utc)
        count = (
            self.db.query(RefreshToken)
            .filter(
                and_(
                    RefreshToken.expires_at < now,
                    RefreshToken.revoked_at.isnot(None),
                )
            )
            .delete()
        )
        self.db.commit()
        return count

