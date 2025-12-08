from typing import Generator

from sqlalchemy.orm import Session

from app.core.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that provides a database session.

    Yields:
        Session: SQLAlchemy database session
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

