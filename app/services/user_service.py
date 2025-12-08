from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service for user business logic."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.repository = UserRepository(db)

    def create_user(self, user_data: UserCreate) -> dict:
        """Create a new user with business logic validation."""
        # Check if user already exists
        existing_user = self.repository.get_by_email(user_data.email)
        if existing_user:
            raise ValueError(f"User with email {user_data.email} already exists")

        # Create user
        user = self.repository.create(user_data.model_dump())
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

    def update_user(self, user_id: UUID, user_data: UserUpdate) -> dict | None:
        """Update user with business logic validation."""
        user = self.repository.get_by_id(user_id)
        if not user:
            return None

        # Check email uniqueness if email is being updated
        if user_data.email and user_data.email != user.email:
            existing_user = self.repository.get_by_email(user_data.email)
            if existing_user:
                raise ValueError(f"User with email {user_data.email} already exists")

        # Update user
        update_data = user_data.model_dump(exclude_unset=True)
        updated_user = self.repository.update(user, update_data)
        return {
            "id": updated_user.id,
            "email": updated_user.email,
            "full_name": updated_user.full_name,
            "is_active": updated_user.is_active,
            "created_at": updated_user.created_at,
            "updated_at": updated_user.updated_at,
        }

    def delete_user(self, user_id: UUID) -> bool:
        """Delete user."""
        user = self.repository.get_by_id(user_id)
        if not user:
            return False
        self.repository.delete(user)
        return True

