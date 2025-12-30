"""Admin user seeder for production environment.

Creates the owner user for production deployments.
This seeder is idempotent - it will not create duplicate users.
"""

from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.seeders.base import Seeder
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole


class AdminUserSeeder(Seeder):
    """Seeder for production admin user.

    Creates:
    - owner@aiutox.com with 'owner' role (full access with * permission)

    This seeder is idempotent - it will not create duplicate users or roles.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get or create default tenant
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
        if not tenant:
            tenant = Tenant(
                name="Default Tenant",
                slug="default",
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)

        # Create owner user
        owner_email = "owner@aiutox.com"
        owner_user = db.query(User).filter(User.email == owner_email).first()

        if not owner_user:
            owner_user = User(
                email=owner_email,
                password_hash=hash_password("password"),
                full_name="System Owner",
                tenant_id=tenant.id,
                is_active=True,
            )
            db.add(owner_user)
            db.commit()
            db.refresh(owner_user)

        # Check if owner role exists
        owner_role = (
            db.query(UserRole)
            .filter(UserRole.user_id == owner_user.id, UserRole.role == "owner")
            .first()
        )

        if not owner_role:
            role = UserRole(
                user_id=owner_user.id,
                role="owner",
                granted_by=owner_user.id,  # Self-granted for initial setup
            )
            db.add(role)
            db.commit()














