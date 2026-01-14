from uuid import UUID
import logging

from sqlalchemy.orm import Session

from app.core.auth.password import hash_password
from app.core.logging import create_audit_log_entry, log_user_action
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class UserService:
    """Service for user business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.repository = UserRepository(db)

    def create_user(
        self,
        user_data: UserCreate,
        created_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Create a new user with business logic validation.

        Args:
            user_data: User creation data.
            created_by: UUID of user who created this user (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        # Check if user already exists
        existing_user = self.repository.get_by_email(user_data.email)
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")

        # Hash password before creating user
        user_dict = user_data.model_dump()
        user_dict["password_hash"] = hash_password(user_dict.pop("password"))

        # Create user
        user = self.repository.create(user_dict)

        # Log user creation
        if created_by:
            # Get tenant_id from creator
            creator = self.repository.get_by_id(created_by)
            if creator:
                log_user_action(
                    action="create_user",
                    user_id=str(created_by),
                    target_user_id=str(user.id),
                    tenant_id=str(creator.tenant_id),
                    details={"email": user.email, "full_name": user.full_name},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                create_audit_log_entry(
                    db=self.repository.db,
                    user_id=created_by,
                    tenant_id=creator.tenant_id,
                    action="create_user",
                    resource_type="user",
                    resource_id=user.id,
                    details={"email": user.email, "full_name": user.full_name},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
        }

    def get_user(self, user_id: UUID) -> dict | None:
        """Get user by ID."""
        user = self.repository.get_by_id(user_id)
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "tenant_id": user.tenant_id,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def get_user_by_email(self, email: str) -> dict | None:
        """Get user by email."""
        user = self.repository.get_by_email(email)
        if not user:
            return None
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
        }

    def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate,
        updated_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict | None:
        """
        Update user with business logic validation.

        Args:
            user_id: User ID to update.
            user_data: User update data.
            updated_by: UUID of user who updated this user (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            return None

        # Track changes for audit log
        changes = {}

        # Check email uniqueness if email is being updated
        if user_data.email and user_data.email != user.email:
            existing_user = self.repository.get_by_email(user_data.email)
            if existing_user:
                raise ValueError(f"User with email {user_data.email} already exists")
            changes["email"] = {"old": user.email, "new": user_data.email}

        # Track other important changes
        update_data = user_data.model_dump(exclude_unset=True)
        if "full_name" in update_data and update_data["full_name"] != user.full_name:
            changes["full_name"] = {"old": user.full_name, "new": update_data["full_name"]}

        # If user is being deactivated, revoke all tokens
        tokens_revoked = 0
        if "is_active" in update_data and update_data["is_active"] != user.is_active:
            changes["is_active"] = {"old": user.is_active, "new": update_data["is_active"]}
            # If being deactivated, revoke all tokens
            if update_data["is_active"] is False:
                from app.repositories.refresh_token_repository import RefreshTokenRepository
                refresh_token_repo = RefreshTokenRepository(self.repository.db)
                tokens_revoked = refresh_token_repo.revoke_all_user_tokens(user_id)
                if tokens_revoked > 0:
                    changes["tokens_revoked"] = tokens_revoked

        # Update user
        logger.debug(f"[update_user] Calling repository.update with update_data: {update_data}")
        updated_user = self.repository.update(user, update_data)
        logger.debug(f"[update_user] Repository.update returned user with avatar_url: {updated_user.avatar_url}")

        # Log user update (only if there are significant changes)
        if updated_by and changes:
            updater = self.repository.get_by_id(updated_by)
            if updater:
                log_user_action(
                    action="update_user",
                    user_id=str(updated_by),
                    target_user_id=str(user_id),
                    tenant_id=str(updater.tenant_id),
                    details={"changes": changes},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                create_audit_log_entry(
                    db=self.repository.db,
                    user_id=updated_by,
                    tenant_id=updater.tenant_id,
                    action="update_user",
                    resource_type="user",
                    resource_id=user_id,
                    details={"changes": changes},
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

        return {
            "id": updated_user.id,
            "email": updated_user.email,
            "first_name": updated_user.first_name,
            "last_name": updated_user.last_name,
            "middle_name": updated_user.middle_name,
            "full_name": updated_user.full_name,
            "date_of_birth": updated_user.date_of_birth,
            "gender": updated_user.gender,
            "nationality": updated_user.nationality,
            "marital_status": updated_user.marital_status,
            "job_title": updated_user.job_title,
            "department": updated_user.department,
            "employee_id": updated_user.employee_id,
            "preferred_language": updated_user.preferred_language,
            "timezone": updated_user.timezone,
            "avatar_url": updated_user.avatar_url,
            "bio": updated_user.bio,
            "notes": updated_user.notes,
            "is_active": updated_user.is_active,
            "two_factor_enabled": updated_user.two_factor_enabled,
            "tenant_id": updated_user.tenant_id,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
            "last_login_at": updated_user.last_login_at,
            "email_verified_at": updated_user.email_verified_at,
            "phone_verified_at": updated_user.phone_verified_at,
        }

    def deactivate_user(
        self,
        user_id: UUID,
        deactivated_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Soft delete user (set is_active=False) and revoke all tokens.

        Args:
            user_id: User ID to deactivate.
            deactivated_by: UUID of user who deactivated this user (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            return False

        tenant_id = user.tenant_id

        # Revoke all refresh tokens for this user
        from app.repositories.refresh_token_repository import RefreshTokenRepository
        refresh_token_repo = RefreshTokenRepository(self.repository.db)
        tokens_revoked = refresh_token_repo.revoke_all_user_tokens(user_id)

        # Set user as inactive
        user.is_active = False
        self.repository.update(user, {})

        # Log user deactivation
        if deactivated_by:
            log_user_action(
                action="deactivate_user",
                user_id=str(deactivated_by),
                target_user_id=str(user_id),
                tenant_id=str(tenant_id),
                details={"email": user.email, "tokens_revoked": tokens_revoked},
                ip_address=ip_address,
                user_agent=user_agent,
            )

            create_audit_log_entry(
                db=self.repository.db,
                user_id=deactivated_by,
                tenant_id=tenant_id,
                action="deactivate_user",
                resource_type="user",
                resource_id=user_id,
                details={"email": user.email, "tokens_revoked": tokens_revoked},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return True

    def delete_user(
        self,
        user_id: UUID,
        deleted_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Hard delete user (permanent deletion with cascade).

        Args:
            user_id: User ID to delete.
            deleted_by: UUID of user who deleted this user (None for system).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        user = self.repository.get_by_id(user_id)
        if not user:
            return False

        tenant_id = user.tenant_id
        user_email = user.email

        # Log user deletion before deleting
        if deleted_by:
            log_user_action(
                action="delete_user",
                user_id=str(deleted_by),
                target_user_id=str(user_id),
                tenant_id=str(tenant_id),
                details={"email": user_email},
                ip_address=ip_address,
                user_agent=user_agent,
            )

            create_audit_log_entry(
                db=self.repository.db,
                user_id=deleted_by,
                tenant_id=tenant_id,
                action="delete_user",
                resource_type="user",
                resource_id=user_id,
                details={"email": user_email},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        # Hard delete with cascade (handled by SQLAlchemy relationships)
        self.repository.delete(user)

        return True

    def list_users(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
    ) -> tuple[list[dict], int]:
        """
        List users by tenant with pagination and optional filters.

        Args:
            tenant_id: Tenant UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            filters: Dictionary with filter conditions:
                - search: str - Search in email, first_name, last_name
                - is_active: bool - Filter by active status

        Returns:
            Tuple of (list of user dicts, total count).
        """
        users, total = self.repository.get_all_by_tenant(
            tenant_id=tenant_id, skip=skip, limit=limit, filters=filters or {}
        )

        user_dicts = [
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
            for user in users
        ]

        return user_dicts, total

    def bulk_action(
        self,
        user_ids: list[UUID],
        action: str,
        tenant_id: UUID,
        performed_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """
        Perform bulk action on users.

        Args:
            user_ids: List of user IDs.
            action: Action to perform (activate, deactivate, delete).
            tenant_id: Tenant ID for security.
            performed_by: User performing the action.
            ip_address: Client IP address.
            user_agent: Client user agent.

        Returns:
            Dictionary with success and failed counts.
        """
        success_count = 0
        failed_count = 0
        failed_ids = []

        for user_id in user_ids:
            try:
                user = self.repository.get_by_id(user_id)

                # Verify that the user exists and belongs to the tenant
                if not user or user.tenant_id != tenant_id:
                    failed_count += 1
                    failed_ids.append(str(user_id))
                    continue

                # Apply action
                if action == "activate":
                    update_data = {"is_active": True}
                    self.repository.update(user, update_data)

                    # Log audit entry
                    if performed_by:
                        log_user_action(
                            action="bulk_activate_user",
                            user_id=str(performed_by),
                            target_user_id=str(user_id),
                            tenant_id=str(tenant_id),
                            details={"action": action, "email": user.email},
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                        create_audit_log_entry(
                            db=self.repository.db,
                            user_id=performed_by,
                            tenant_id=tenant_id,
                            action="bulk_activate_user",
                            resource_type="user",
                            resource_id=user_id,
                            details={"action": action, "email": user.email},
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                    success_count += 1

                elif action == "deactivate":
                    # Soft delete (set is_active=False) and revoke tokens
                    # Revoke all refresh tokens for this user
                    from app.repositories.refresh_token_repository import RefreshTokenRepository
                    refresh_token_repo = RefreshTokenRepository(self.repository.db)
                    tokens_revoked = refresh_token_repo.revoke_all_user_tokens(user_id)

                    # Set user as inactive
                    update_data = {"is_active": False}
                    self.repository.update(user, update_data)

                    # Log audit entry
                    if performed_by:
                        log_user_action(
                            action="bulk_deactivate_user",
                            user_id=str(performed_by),
                            target_user_id=str(user_id),
                            tenant_id=str(tenant_id),
                            details={"action": action, "email": user.email, "tokens_revoked": tokens_revoked},
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                        create_audit_log_entry(
                            db=self.repository.db,
                            user_id=performed_by,
                            tenant_id=tenant_id,
                            action="bulk_deactivate_user",
                            resource_type="user",
                            resource_id=user_id,
                            details={"action": action, "email": user.email, "tokens_revoked": tokens_revoked},
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                    success_count += 1

                elif action == "delete":
                    # Soft delete (set is_active=False) and revoke tokens
                    # Revoke all refresh tokens for this user
                    from app.repositories.refresh_token_repository import RefreshTokenRepository
                    refresh_token_repo = RefreshTokenRepository(self.repository.db)
                    tokens_revoked = refresh_token_repo.revoke_all_user_tokens(user_id)

                    user_email = user.email

                    # Log before deletion
                    if performed_by:
                        log_user_action(
                            action="bulk_delete_user",
                            user_id=str(performed_by),
                            target_user_id=str(user_id),
                            tenant_id=str(tenant_id),
                            details={"action": action, "email": user_email, "tokens_revoked": tokens_revoked},
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                        create_audit_log_entry(
                            db=self.repository.db,
                            user_id=performed_by,
                            tenant_id=tenant_id,
                            action="bulk_delete_user",
                            resource_type="user",
                            resource_id=user_id,
                            details={"action": action, "email": user_email, "tokens_revoked": tokens_revoked},
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                    # Soft delete (set is_active=False)
                    update_data = {"is_active": False}
                    self.repository.update(user, update_data)
                    success_count += 1

                else:
                    failed_count += 1
                    failed_ids.append(str(user_id))
                    continue

            except Exception as e:
                failed_count += 1
                failed_ids.append(str(user_id))
                # Log error but continue with other users
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in bulk action for user {user_id}: {e}")

        return {
            "success": success_count,
            "failed": failed_count,
            "failed_ids": failed_ids,
        }
