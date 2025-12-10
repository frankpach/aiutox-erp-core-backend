"""Database seeder - Main seeder that calls other seeders."""

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder


class DatabaseSeeder(Seeder):
    """Main database seeder.

    This seeder can call other seeders in order.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Example: Call other seeders
        # from database.seeders.user_seeder import UserSeeder
        # UserSeeder().run(db)
        pass

