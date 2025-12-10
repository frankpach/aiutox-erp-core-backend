"""Seeder manager for executing and tracking seeders."""

import importlib
import sys
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.db.session import Base, SessionLocal, engine
from app.core.seeders.base import Seeder
from app.core.seeders.models import SeederRecord


class SeederManager:
    """Manager for executing and tracking database seeders."""

    def __init__(self, seeders_dir: Optional[Path] = None):
        """Initialize seeder manager.

        Args:
            seeders_dir: Directory containing seeder files. Defaults to backend/database/seeders/
        """
        if seeders_dir is None:
            backend_dir = Path(__file__).parent.parent.parent.parent
            seeders_dir = backend_dir / "database" / "seeders"

        self.seeders_dir = seeders_dir
        self.seeders_dir.mkdir(parents=True, exist_ok=True)

        # Ensure seeders table exists
        Base.metadata.create_all(bind=engine, tables=[SeederRecord.__table__])

    def _get_seeder_files(self) -> List[Path]:
        """Get all seeder files from seeders directory.

        Returns:
            List of seeder file paths
        """
        if not self.seeders_dir.exists():
            return []

        seeders = []
        for file_path in sorted(self.seeders_dir.glob("*.py")):
            if file_path.name in ("__init__.py", "base.py"):
                continue
            seeders.append(file_path)

        return seeders

    def _load_seeder_class(self, file_path: Path) -> type[Seeder]:
        """Load seeder class from file.

        Args:
            file_path: Path to seeder file

        Returns:
            Seeder class

        Raises:
            ImportError: If seeder class cannot be loaded
        """
        # Add seeders directory to path
        seeders_parent = file_path.parent.parent
        if str(seeders_parent) not in sys.path:
            sys.path.insert(0, str(seeders_parent))

        # Import module
        module_name = f"database.seeders.{file_path.stem}"
        module = importlib.import_module(module_name)

        # Find Seeder subclass
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, Seeder)
                and attr is not Seeder
                and attr.__module__ == module_name
            ):
                return attr

        raise ImportError(f"No Seeder class found in {file_path}")

    def get_executed_seeders(self, db: Session) -> List[str]:
        """Get list of executed seeder names.

        Args:
            db: Database session

        Returns:
            List of seeder names that have been executed
        """
        records = db.query(SeederRecord).all()
        return [record.seeder_name for record in records]

    def get_pending_seeders(self, db: Session) -> List[type[Seeder]]:
        """Get list of pending seeders.

        Args:
            db: Database session

        Returns:
            List of seeder classes that haven't been executed
        """
        executed = set(self.get_executed_seeders(db))
        pending = []

        for file_path in self._get_seeder_files():
            try:
                seeder_class = self._load_seeder_class(file_path)
                seeder_name = seeder_class.__name__

                if seeder_name not in executed:
                    pending.append(seeder_class)
            except Exception:
                # Skip files that can't be loaded
                continue

        return pending

    def execute_seeder(self, seeder_class: type[Seeder], db: Session) -> None:
        """Execute a seeder and record it.

        Args:
            seeder_class: Seeder class to execute
            db: Database session
        """
        seeder = seeder_class()
        seeder_name = seeder.get_name()

        # Check if already executed
        existing = db.query(SeederRecord).filter(SeederRecord.seeder_name == seeder_name).first()
        if existing:
            return

        # Execute seeder
        seeder.run(db)

        # Record execution
        record = SeederRecord(seeder_name=seeder_name)
        db.add(record)
        db.commit()

    def run_all(self, db: Optional[Session] = None) -> dict:
        """Run all pending seeders.

        Args:
            db: Database session. If None, creates a new one.

        Returns:
            Dictionary with execution results
        """
        if db is None:
            db = SessionLocal()
            try:
                return self.run_all(db)
            finally:
                db.close()

        pending = self.get_pending_seeders(db)
        executed = []

        for seeder_class in pending:
            try:
                self.execute_seeder(seeder_class, db)
                executed.append(seeder_class.__name__)
            except Exception as e:
                db.rollback()
                return {
                    "success": False,
                    "error": str(e),
                    "executed": executed,
                    "failed": seeder_class.__name__,
                }

        return {
            "success": True,
            "executed": executed,
            "total": len(executed),
        }

    def run_seeder(self, seeder_name: str, db: Optional[Session] = None) -> dict:
        """Run a specific seeder by name.

        Args:
            seeder_name: Name of seeder class
            db: Database session. If None, creates a new one.

        Returns:
            Dictionary with execution result
        """
        if db is None:
            db = SessionLocal()
            try:
                return self.run_seeder(seeder_name, db)
            finally:
                db.close()

        # Find seeder file
        for file_path in self._get_seeder_files():
            try:
                seeder_class = self._load_seeder_class(file_path)
                if seeder_class.__name__ == seeder_name:
                    self.execute_seeder(seeder_class, db)
                    return {
                        "success": True,
                        "executed": [seeder_name],
                    }
            except Exception:
                continue

        return {
            "success": False,
            "error": f"Seeder '{seeder_name}' not found",
        }

    def rollback_last(self, db: Optional[Session] = None) -> dict:
        """Rollback last executed seeder (remove from tracking).

        Args:
            db: Database session. If None, creates a new one.

        Returns:
            Dictionary with rollback result
        """
        if db is None:
            db = SessionLocal()
            try:
                return self.rollback_last(db)
            finally:
                db.close()

        # Get last executed seeder
        last_record = db.query(SeederRecord).order_by(SeederRecord.executed_at.desc()).first()

        if not last_record:
            return {
                "success": False,
                "error": "No seeders to rollback",
            }

        seeder_name = last_record.seeder_name
        db.delete(last_record)
        db.commit()

        return {
            "success": True,
            "rolled_back": seeder_name,
        }

