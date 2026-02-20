"""Development users seeder for development environment.

Creates multiple users with different permission levels for testing:
- owner: Full access to verify complete module functionality
- admin: Global permissions management
- supervisor: Module-specific permissions management
- user: Basic user without permissions (for permission delegation testing)

This seeder is idempotent - it will not create duplicate users or roles.
"""

from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.seeders.base import Seeder
from app.models.module_role import ModuleRole
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole


class DevelopmentUsersSeeder(Seeder):
    """Seeder for development users with different permission levels.

    Creates:
    - owner@aiutox.com: 'owner' role (full access with * permission)
    - admin@aiutox.com: 'admin' role (global permissions management)
    - supervisor@aiutox.com: 'manager' role + module roles (module-specific permissions)
    - user@aiutox.com: No roles (basic user for permission delegation testing)

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

        # Get or create owner user (for granting roles to others)
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

        # Ensure owner has owner role
        owner_role = (
            db.query(UserRole)
            .filter(UserRole.user_id == owner_user.id, UserRole.role == "owner")
            .first()
        )
        if not owner_role:
            role = UserRole(
                user_id=owner_user.id,
                role="owner",
                granted_by=owner_user.id,
            )
            db.add(role)
            db.commit()

        # Create admin user
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

        # Ensure admin has admin role
        admin_role = (
            db.query(UserRole)
            .filter(UserRole.user_id == admin_user.id, UserRole.role == "admin")
            .first()
        )
        if not admin_role:
            role = UserRole(
                user_id=admin_user.id,
                role="admin",
                granted_by=owner_user.id,
            )
            db.add(role)
            db.commit()

        # Create supervisor user
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

        # Ensure supervisor has manager role (global)
        supervisor_manager_role = (
            db.query(UserRole)
            .filter(UserRole.user_id == supervisor_user.id, UserRole.role == "manager")
            .first()
        )
        if not supervisor_manager_role:
            role = UserRole(
                user_id=supervisor_user.id,
                role="manager",
                granted_by=admin_user.id,
            )
            db.add(role)
            db.commit()

        # Assign module roles to supervisor (internal.manager for inventory and products)
        # This allows supervisor to delegate permissions in these modules
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
                    role_name="manager",  # Stored without "internal." prefix
                    granted_by=admin_user.id,
                )
                db.add(module_role)
                db.commit()

        # Create basic user (no roles, no permissions)
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
