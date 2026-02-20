from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config_file import get_settings

settings = get_settings()

# Detectar tipo de base de datos y configurar apropiadamente
database_url = settings.database_url

if database_url.startswith("sqlite"):
    # Configuración para SQLite (más rápida para desarrollo)
    engine = create_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
    )
else:
    # Configuración para PostgreSQL
    engine = create_engine(
        database_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={"connect_timeout": 10, "options": "-c timezone=utc"},
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
