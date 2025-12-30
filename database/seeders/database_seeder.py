"""Database seeder - Main seeder that calls other seeders."""

from sqlalchemy.orm import Session

from app.core.config_file import get_settings
from app.core.seeders.base import Seeder


class DatabaseSeeder(Seeder):
    """Main database seeder.

    This seeder calls other seeders based on the environment:
    - Production: Only AdminUserSeeder (creates owner user)
    - Development: DevelopmentUsersSeeder (creates owner, admin, supervisor, user)

    This seeder is idempotent - it will not create duplicate data.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        settings = get_settings()
        is_production = settings.ENV.lower() in ("prod", "production")

        # Import seeders
        from database.seeders.config_seeder import ConfigSeeder
        from database.seeders.default_tenant_seeder import DefaultTenantSeeder
        from database.seeders.theme_seeder import ThemeSeeder
        from database.seeders.theme_preset_seeder import ThemePresetSeeder

        # Always create default tenant first (required for all other seeders)
        DefaultTenantSeeder().run(db)

        if is_production:
            # Production: Only create owner user
            from database.seeders.admin_user_seeder import AdminUserSeeder

            AdminUserSeeder().run(db)
        else:
            # Development: Create all test users
            from database.seeders.development_users_seeder import (
                DevelopmentUsersSeeder,
            )

            DevelopmentUsersSeeder().run(db)

        # Always seed configuration and theme for all environments
        ConfigSeeder().run(db)
        ThemeSeeder().run(db)
        ThemePresetSeeder().run(db)

