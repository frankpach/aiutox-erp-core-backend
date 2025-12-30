"""Script to create admin user for E2E tests."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import hash_password
from app.core.config_file import get_settings
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole

# Set test database URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://devuser:devpass@localhost:15432/aiutox_erp_test"
)

# Create engine and session
engine = create_engine(TEST_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_admin_user():
    """Create admin user for E2E tests."""
    db = SessionLocal()
    try:
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
            print(f"Created tenant: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"Using existing tenant: {tenant.name} (ID: {tenant.id})")

        # Check if admin user already exists
        admin_email = "admin@aiutox.com"
        admin_user = db.query(User).filter(User.email == admin_email).first()

        if admin_user:
            print(f"Admin user {admin_email} already exists (ID: {admin_user.id})")
            # Check if user has admin role
            admin_role = db.query(UserRole).filter(
                UserRole.user_id == admin_user.id,
                UserRole.role == "admin"
            ).first()
            if not admin_role:
                # Add admin role
                role = UserRole(
                    user_id=admin_user.id,
                    role="admin",
                    granted_by=admin_user.id,
                )
                db.add(role)
                db.commit()
                print(f"Added admin role to user {admin_email}")
            else:
                print(f"User {admin_email} already has admin role")
        else:
            # Create admin user
            admin_user = User(
                email=admin_email,
                password_hash=hash_password("password"),
                full_name="Admin User",
                tenant_id=tenant.id,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"Created admin user: {admin_email} (ID: {admin_user.id})")

            # Add admin role
            role = UserRole(
                user_id=admin_user.id,
                role="admin",
                granted_by=admin_user.id,
            )
            db.add(role)
            db.commit()
            print(f"Added admin role to user {admin_email}")

        print("[SUCCESS] Admin user setup complete!")
        print(f"   Email: {admin_email}")
        print(f"   Password: password")
        print(f"   Tenant: {tenant.name}")

    except Exception as e:
        print(f"[ERROR] Error creating admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()














