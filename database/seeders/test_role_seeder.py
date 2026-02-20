"""Test role seeder for test database."""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole


class TestRoleSeeder(Seeder):
    """Seeder for test role data.

    Assigns roles to test users:
    - admin@test.example.com gets 'admin' role
    - user@test.example.com gets 'staff' role

    This seeder is idempotent - it will not create duplicate roles.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get test tenant
        test_tenant = db.query(Tenant).filter(Tenant.slug == "test-default").first()
        if not test_tenant:
            return  # Tenant doesn't exist, skip

        # Get admin user
        admin_user = (
            db.query(User).filter(User.email == "admin@test.example.com").first()
        )
        if admin_user:
            # Check if role already exists
            existing_role = (
                db.query(UserRole)
                .filter(UserRole.user_id == admin_user.id, UserRole.role == "admin")
                .first()
            )
            if not existing_role:
                admin_role = UserRole(
                    user_id=admin_user.id,
                    role="admin",
                    granted_by=admin_user.id,  # Self-granted for tests
                )
                db.add(admin_role)
                db.commit()

        # Get regular user
        regular_user = (
            db.query(User).filter(User.email == "user@test.example.com").first()
        )
        if regular_user:
            # Check if role already exists
            existing_role = (
                db.query(UserRole)
                .filter(UserRole.user_id == regular_user.id, UserRole.role == "staff")
                .first()
            )
            if not existing_role:
                staff_role = UserRole(
                    user_id=regular_user.id,
                    role="staff",
                    granted_by=admin_user.id if admin_user else regular_user.id,
                )
                db.add(staff_role)
                db.commit()
