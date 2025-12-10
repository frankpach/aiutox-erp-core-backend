"""Test user seeder for test database."""

from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.seeders.base import Seeder
from app.models.tenant import Tenant
from app.models.user import User


class TestUserSeeder(Seeder):
    """Seeder for test user data.

    Creates test users for use in tests:
    - admin@test.example.com (admin user)
    - user@test.example.com (regular user)
    - inactive@test.example.com (inactive user)

    This seeder is idempotent - it will not create duplicate users.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get or create test tenant
        test_tenant = db.query(Tenant).filter(Tenant.slug == "test-default").first()
        if not test_tenant:
            # Create test tenant if it doesn't exist
            test_tenant = Tenant(
                name="Test Tenant",
                slug="test-default",
            )
            db.add(test_tenant)
            db.commit()
            db.refresh(test_tenant)

        # Create admin user
        admin_email = "admin@test.example.com"
        if not db.query(User).filter(User.email == admin_email).first():
            admin_user = User(
                email=admin_email,
                password_hash=hash_password("password"),
                full_name="Test Admin",
                tenant_id=test_tenant.id,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()

        # Create regular user
        user_email = "user@test.example.com"
        if not db.query(User).filter(User.email == user_email).first():
            regular_user = User(
                email=user_email,
                password_hash=hash_password("password"),
                full_name="Test User",
                tenant_id=test_tenant.id,
                is_active=True,
            )
            db.add(regular_user)
            db.commit()

        # Create inactive user
        inactive_email = "inactive@test.example.com"
        if not db.query(User).filter(User.email == inactive_email).first():
            inactive_user = User(
                email=inactive_email,
                password_hash=hash_password("password"),
                full_name="Inactive User",
                tenant_id=test_tenant.id,
                is_active=False,
            )
            db.add(inactive_user)
            db.commit()
