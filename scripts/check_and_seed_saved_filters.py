"""Script to check and seed saved filters for testing.

This script:
1. Checks how many saved filters exist in the database
2. Creates test filters if none exist:
   - One filter for 'users' module
   - One filter for 'products' module (or another module)
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.db.deps import get_db
from app.models.view import SavedFilter
from app.models.user import User
from app.models.tenant import Tenant


def check_saved_filters(db: Session) -> dict:
    """Check how many saved filters exist."""
    total_count = db.query(SavedFilter).count()

    # Count by module
    modules = db.query(SavedFilter.module).distinct().all()
    module_counts = {}
    for (module,) in modules:
        count = db.query(SavedFilter).filter(SavedFilter.module == module).count()
        module_counts[module] = count

    # Count by tenant
    tenants = db.query(SavedFilter.tenant_id).distinct().all()
    tenant_counts = {}
    for (tenant_id,) in tenants:
        count = db.query(SavedFilter).filter(SavedFilter.tenant_id == tenant_id).count()
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        tenant_name = tenant.name if tenant else str(tenant_id)
        tenant_counts[tenant_name] = count

    return {
        "total": total_count,
        "by_module": module_counts,
        "by_tenant": tenant_counts,
    }


def create_test_filters(db: Session) -> list[SavedFilter]:
    """Create test saved filters if they don't exist."""
    # Get default tenant
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if not default_tenant:
        # Try to get any tenant
        default_tenant = db.query(Tenant).first()
        if not default_tenant:
            print("ERROR: No tenant found. Please run seeders first.")
            return []

    # Get admin user
    admin_user = db.query(User).filter(User.email == "admin@aiutox.com").first()
    if not admin_user:
        # Try owner user
        admin_user = db.query(User).filter(User.email == "owner@aiutox.com").first()
        if not admin_user:
            # Get any user
            admin_user = db.query(User).first()
            if not admin_user:
                print("ERROR: No user found. Please run seeders first.")
                return []

    created_filters = []

    # Check if users filter exists
    users_filter = db.query(SavedFilter).filter(
        SavedFilter.module == "users",
        SavedFilter.tenant_id == default_tenant.id
    ).first()

    if not users_filter:
        users_filter = SavedFilter(
            id=uuid4(),
            tenant_id=default_tenant.id,
            name="Usuarios Activos",
            description="Filtro para mostrar solo usuarios activos",
            module="users",
            filters={"is_active": True},
            is_default=False,
            created_by=admin_user.id,
            is_shared=True,
        )
        db.add(users_filter)
        created_filters.append(users_filter)
        print(f"✓ Created filter 'Usuarios Activos' for 'users' module")
    else:
        print(f"✓ Filter 'users' module already exists: {users_filter.name}")

    # Check if products filter exists
    products_filter = db.query(SavedFilter).filter(
        SavedFilter.module == "products",
        SavedFilter.tenant_id == default_tenant.id
    ).first()

    if not products_filter:
        products_filter = SavedFilter(
            id=uuid4(),
            tenant_id=default_tenant.id,
            name="Productos Disponibles",
            description="Filtro para mostrar solo productos disponibles",
            module="products",
            filters={"is_active": True, "stock_quantity": {"gt": 0}},
            is_default=False,
            created_by=admin_user.id,
            is_shared=False,
        )
        db.add(products_filter)
        created_filters.append(products_filter)
        print(f"✓ Created filter 'Productos Disponibles' for 'products' module")
    else:
        print(f"✓ Filter 'products' module already exists: {products_filter.name}")

    if created_filters:
        db.commit()
        for filter_obj in created_filters:
            db.refresh(filter_obj)
        print(f"\n✓ Created {len(created_filters)} new filter(s)")
    else:
        print("\n✓ All test filters already exist")

    return created_filters


def main():
    """Main function."""
    print("=" * 60)
    print("Saved Filters Checker and Seeder")
    print("=" * 60)
    print()

    # Get database session
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        # Check existing filters
        print("Checking existing saved filters...")
        stats = check_saved_filters(db)

        print(f"\nTotal saved filters: {stats['total']}")

        if stats['by_module']:
            print("\nBy module:")
            for module, count in stats['by_module'].items():
                print(f"  - {module}: {count}")
        else:
            print("\nNo filters found by module")

        if stats['by_tenant']:
            print("\nBy tenant:")
            for tenant, count in stats['by_tenant'].items():
                print(f"  - {tenant}: {count}")
        else:
            print("\nNo filters found by tenant")

        print("\n" + "-" * 60)

        # Create test filters if needed
        if stats['total'] == 0:
            print("\nNo filters found. Creating test filters...")
            create_test_filters(db)
        else:
            print("\nFilters exist. Checking if test filters are needed...")
            create_test_filters(db)

        print("\n" + "=" * 60)
        print("Done!")
        print("=" * 60)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()

