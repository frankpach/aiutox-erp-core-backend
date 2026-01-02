"""Default tenant seeder.

Creates a default tenant if it doesn't exist.
This seeder ensures that there's always a tenant available for the system.
"""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.tenant import Tenant


class DefaultTenantSeeder(Seeder):
    """Seeder for default tenant.

    Creates:
    - A tenant with slug "default" and name "Default Tenant"

    This seeder is idempotent - it will not create duplicate tenants.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Check if default tenant exists
        tenant = db.query(Tenant).filter(Tenant.slug == "default").first()

        if not tenant:
            tenant = Tenant(
                name="Default Tenant",
                slug="default",
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✅ DefaultTenantSeeder: Created default tenant (ID: {tenant.id})")
        else:
            print(f"✅ DefaultTenantSeeder: Default tenant already exists (ID: {tenant.id})")



