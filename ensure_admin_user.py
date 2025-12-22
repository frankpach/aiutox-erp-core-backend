"""Script to ensure admin/owner user exists and has appropriate roles.

This script can work in two modes:
- Production: Ensures owner@aiutox.com exists with 'owner' role
- Development: Ensures all development users exist (owner, admin, supervisor, user)

Usage:
    python ensure_admin_user.py              # Auto-detect environment
    python ensure_admin_user.py --dev        # Force development mode
    python ensure_admin_user.py --prod       # Force production mode
"""
import sys
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.config_file import get_settings
from app.core.db.session import SessionLocal
from app.models.module_role import ModuleRole
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole


def ensure_admin_user(force_dev: bool = False, force_prod: bool = False):
    """Ensure admin/owner user exists and has appropriate roles.

    Args:
        force_dev: Force development mode (create all users)
        force_prod: Force production mode (create only owner)
    """
    settings = get_settings()
    db: Session = SessionLocal()

    # Determine mode
    if force_dev:
        is_production = False
        mode = "development (forced)"
    elif force_prod:
        is_production = True
        mode = "production (forced)"
    else:
        is_production = settings.ENV.lower() in ("prod", "production")
        mode = "production" if is_production else "development"

    try:
        print(f"[INFO] Mode: {mode}")
        print(f"[INFO] Connecting to database: {settings.POSTGRES_DB} at {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")

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
            print(f"[INFO] Created tenant: {tenant.name} (ID: {tenant.id})")
        else:
            print(f"[INFO] Using existing tenant: {tenant.name} (ID: {tenant.id})")

        if is_production:
            # Production: Only create owner
            return _ensure_owner_user(db, tenant)
        else:
            # Development: Create all users
            return _ensure_development_users(db, tenant)

    except Exception as e:
        print(f"[ERROR] Error ensuring users: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


def _ensure_owner_user(db: Session, tenant: Tenant) -> bool:
    """Ensure owner user exists with owner role."""
    owner_email = "owner@aiutox.com"
    owner_user = db.query(User).filter(User.email == owner_email).first()

    if not owner_user:
        print(f"[WARN] Owner user {owner_email} does not exist. Creating...")
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
        print(f"[SUCCESS] Created owner user: {owner_email} (ID: {owner_user.id})")
    else:
        print(f"[INFO] Owner user {owner_email} exists (ID: {owner_user.id})")

    # Check if user has owner role
    owner_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == owner_user.id, UserRole.role == "owner")
        .first()
    )

    if not owner_role:
        print(f"[WARN] User {owner_email} does not have owner role. Adding...")
        role = UserRole(
            user_id=owner_user.id,
            role="owner",
            granted_by=owner_user.id,
        )
        db.add(role)
        db.commit()
        print(f"[SUCCESS] Added owner role to user {owner_email}")
    else:
        print(f"[INFO] User {owner_email} already has owner role")

    # Verify permissions
    from app.services.permission_service import PermissionService

    permission_service = PermissionService(db)
    permissions = permission_service.get_effective_permissions(owner_user.id)
    print(f"[INFO] User {owner_email} has {len(permissions)} effective permission(s)")
    if "*" in permissions:
        print(f"[INFO] User has full access (* permission)")

    print("\n[SUCCESS] Owner user verification complete!")
    print(f"   Email: {owner_email}")
    print(f"   Password: password")
    print(f"   Tenant: {tenant.name}")
    print(f"   Role: owner")

    return True


def _ensure_development_users(db: Session, tenant: Tenant) -> bool:
    """Ensure all development users exist with appropriate roles."""
    # Get or create owner (needed to grant roles to others)
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
        print(f"[SUCCESS] Created owner user: {owner_email}")

    # Ensure owner has owner role
    owner_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == owner_user.id, UserRole.role == "owner")
        .first()
    )
    if not owner_role:
        role = UserRole(user_id=owner_user.id, role="owner", granted_by=owner_user.id)
        db.add(role)
        db.commit()

    # Create/verify admin user
    admin_email = "admin@aiutox.com"
    admin_user = db.query(User).filter(User.email == admin_email).first()

    if not admin_user:
        admin_user = User(
            email=admin_email,
            password_hash=hash_password("password"),
            full_name="Administrator",
            tenant_id=tenant.id,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        print(f"[SUCCESS] Created admin user: {admin_email}")

    admin_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == admin_user.id, UserRole.role == "admin")
        .first()
    )
    if not admin_role:
        role = UserRole(user_id=admin_user.id, role="admin", granted_by=owner_user.id)
        db.add(role)
        db.commit()

    # Create/verify supervisor user
    supervisor_email = "supervisor@aiutox.com"
    supervisor_user = db.query(User).filter(User.email == supervisor_email).first()

    if not supervisor_user:
        supervisor_user = User(
            email=supervisor_email,
            password_hash=hash_password("password"),
            full_name="Supervisor",
            tenant_id=tenant.id,
            is_active=True,
        )
        db.add(supervisor_user)
        db.commit()
        db.refresh(supervisor_user)
        print(f"[SUCCESS] Created supervisor user: {supervisor_email}")

    # Ensure supervisor has manager role
    supervisor_manager_role = (
        db.query(UserRole)
        .filter(UserRole.user_id == supervisor_user.id, UserRole.role == "manager")
        .first()
    )
    if not supervisor_manager_role:
        role = UserRole(
            user_id=supervisor_user.id, role="manager", granted_by=admin_user.id
        )
        db.add(role)
        db.commit()

    # Assign module roles to supervisor
    modules_for_supervisor = ["inventory", "products"]
    for module in modules_for_supervisor:
        existing_module_role = (
            db.query(ModuleRole)
            .filter(
                ModuleRole.user_id == supervisor_user.id,
                ModuleRole.module == module,
                ModuleRole.role_name == "manager",
            )
            .first()
        )

        if not existing_module_role:
            module_role = ModuleRole(
                user_id=supervisor_user.id,
                module=module,
                role_name="manager",
                granted_by=admin_user.id,
            )
            db.add(module_role)
            db.commit()

    # Create/verify basic user
    user_email = "user@aiutox.com"
    basic_user = db.query(User).filter(User.email == user_email).first()

    if not basic_user:
        basic_user = User(
            email=user_email,
            password_hash=hash_password("password"),
            full_name="Basic User",
            tenant_id=tenant.id,
            is_active=True,
        )
        db.add(basic_user)
        db.commit()
        print(f"[SUCCESS] Created basic user: {user_email}")

    print("\n[SUCCESS] Development users verification complete!")
    print("\nUsers created:")
    print(f"  • {owner_email} (password: password) - Role: owner")
    print(f"  • {admin_email} (password: password) - Role: admin")
    print(f"  • {supervisor_email} (password: password) - Role: manager + module roles")
    print(f"  • {user_email} (password: password) - Role: none (for testing)")

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ensure admin/owner users exist")
    parser.add_argument(
        "--dev", action="store_true", help="Force development mode (create all users)"
    )
    parser.add_argument(
        "--prod", action="store_true", help="Force production mode (create only owner)"
    )
    args = parser.parse_args()

    success = ensure_admin_user(force_dev=args.dev, force_prod=args.prod)
    sys.exit(0 if success else 1)




