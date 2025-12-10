"""Test tenant seeder for test database."""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.tenant import Tenant


class TestTenantSeeder(Seeder):
    """Seeder for test tenant data.

    Creates a default test tenant for use in tests.
    This seeder is idempotent - it will not create duplicate tenants.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Check if test tenant already exists
        existing = db.query(Tenant).filter(Tenant.slug == "test-default").first()
        if existing:
            return  # Already exists, skip

        # Create test tenant
        test_tenant = Tenant(
            name="Test Tenant",
            slug="test-default",
        )
        db.add(test_tenant)
        db.commit()
        db.refresh(test_tenant)
