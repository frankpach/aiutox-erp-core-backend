from uuid import UUID

from sqlalchemy.orm import Session

from app.core.auth.password import hash_password
from app.core.logging import create_audit_log_entry, log_user_action
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


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
        if "is_active" in update_data and update_data["is_active"] != user.is_active:
            changes["is_active"] = {"old": user.is_active, "new": update_data["is_active"]}

        # Update user
        updated_user = self.repository.update(user, update_data)

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
            "full_name": updated_user.full_name,
            "is_active": updated_user.is_active,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
        }

    def delete_user(
        self,
        user_id: UUID,
        deactivated_by: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        """
        Soft delete user (set is_active=False).

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
        user.is_active = False
        self.repository.update(user, {})

        # Log user deactivation
        if deactivated_by:
            log_user_action(
                action="deactivate_user",
                user_id=str(deactivated_by),
                target_user_id=str(user_id),
                tenant_id=str(tenant_id),
                details={"email": user.email},
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
                details={"email": user.email},
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return True

    def list_users(
        self, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[dict], int]:
        """
        List users by tenant with pagination.

        Args:
            tenant_id: Tenant UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (list of user dicts, total count).
        """
        users = self.repository.get_all_by_tenant(tenant_id, skip=skip, limit=limit)
        total = (
            self.repository.db.query(User)
            .filter(User.tenant_id == tenant_id)
            .count()
        )

        user_dicts = [
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
            for user in users
        ]

        return user_dicts, total

