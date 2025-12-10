"""Base seeder class."""

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session


class Seeder(ABC):
    """Base class for database seeders."""

    @abstractmethod
    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        pass

    def get_name(self) -> str:
        """Get seeder class name.

        Returns:
            Seeder class name
        """
        return self.__class__.__name__

