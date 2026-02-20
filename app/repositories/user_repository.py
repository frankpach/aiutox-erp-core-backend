"""User repository for data access operations."""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.auth.password import verify_password
from app.models.user import User


class UserRepository:
    """Repository for user data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, user_data: dict) -> User:
        """Create a new user."""
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        return (
            self.db.query(User)
            .options(joinedload(User.tenant))
            .filter(User.id == user_id)
            .first()
        )

    def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        import logging

        logger = logging.getLogger("app")
        logger.debug(f"[DB] Starting query for email={email}")
        logger.debug(f"[DB] DB session type: {type(self.db)}")
        logger.debug(
            f"[DB] DB session is active: {self.db.is_active if hasattr(self.db, 'is_active') else 'N/A'}"
        )

        try:
            query = self.db.query(User).filter(User.email == email)
            logger.debug(f"[DB] Query created: {query}")
            result = query.first()
            logger.debug(f"[DB] Query executed, result={result is not None}")
            return result
        except Exception as e:
            logger.error(f"[DB] Error in get_by_email: {e}", exc_info=True)
            raise

    def get_by_email_and_tenant(self, email: str, tenant_id: UUID) -> User | None:
        """Get user by email and tenant ID."""
        return (
            self.db.query(User)
            .filter(User.email == email, User.tenant_id == tenant_id)
            .first()
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all users with pagination."""
        return self.db.query(User).offset(skip).limit(limit).all()

    def get_all_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
    ) -> tuple[list[User], int]:
        """
        Get all users by tenant with pagination and optional filters.

        Args:
            tenant_id: Tenant ID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            filters: Dictionary with filter conditions:
                - search: str - Search in email, first_name, last_name
                - is_active: bool - Filter by active status

        Returns:
            Tuple of (list of users, total count).
        """
        query = self.db.query(User).filter(User.tenant_id == tenant_id)

        # Apply filters
        if filters:
            # Search filter (email, first_name, last_name)
            if "search" in filters and filters["search"]:
                search_term = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        User.email.ilike(search_term),
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
                    )
                )

            # Active status filter
            if "is_active" in filters and filters["is_active"] is not None:
                query = query.filter(User.is_active == filters["is_active"])

        # Get total count before pagination
        total = query.count()

        # Apply pagination
        users = query.offset(skip).limit(limit).all()

        return users, total

    def verify_password(self, user: User, password: str) -> bool:
        """Verify user password against stored hash."""
        return verify_password(password, user.password_hash)

    def update(self, user: User, user_data: dict) -> User:
        """Update user data."""
        for key, value in user_data.items():
            if value is not None:
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: User) -> None:
        """Delete a user."""
        self.db.delete(user)
        self.db.commit()
