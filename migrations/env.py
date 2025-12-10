from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool, text

from app.core.config import get_settings
from app.core.db.session import Base

# Import all models so Alembic can detect them
from app.models import (  # noqa: F401
    AuditLog,
    Contact,
    ContactMethod,
    ModuleRole,
    Organization,
    PersonIdentification,
    RefreshToken,
    Tenant,
    User,
    UserRole,
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# add your model's MetaData object here
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Get database URL from settings directly to avoid encoding issues
    # Use create_engine directly with the URL from settings
    database_url = settings.DATABASE_URL

    # Create engine directly to avoid encoding issues with engine_from_config
    # Use connect_args to pass connection parameters directly if URL encoding fails
    connectable = None
    try:
        # First, try with the URL as-is
        connectable = create_engine(
            database_url,
            poolclass=pool.NullPool,
            echo=False,
            future=True,
            # Explicitly set client encoding
            connect_args={
                "options": "-c client_encoding=utf8",
            },
        )
        # Test the connection to catch encoding errors early
        with connectable.connect() as test_conn:
            test_conn.execute(text("SELECT 1"))
    except (UnicodeDecodeError, UnicodeError, Exception) as e:
        # Check if it's an encoding error
        if isinstance(e, (UnicodeDecodeError, UnicodeError)) or "utf-8" in str(e).lower() or "codec" in str(e).lower():
            # If there's an encoding error, try using connection parameters directly
            import sys
            print(
                "\n⚠️  Warning: Encoding issue detected, trying alternative connection method...",
                file=sys.stderr
            )
            try:
                # Use direct connection parameters to completely bypass URL parsing
                # This avoids all encoding issues with the URL string
                print(
                    "   Using direct connection parameters to avoid encoding issues...",
                    file=sys.stderr
                )

                # Clean password - handle encoding issues more aggressively
                pwd = settings.POSTGRES_PASSWORD
                pwd_str = None

                if isinstance(pwd, bytes):
                    # Decode bytes with error handling - try multiple encodings
                    for encoding in ["utf-8", "latin-1", "cp1252", "iso-8859-1"]:
                        try:
                            pwd_str = pwd.decode(encoding, errors="replace")
                            # Remove replacement characters if any
                            pwd_str = pwd_str.replace("\ufffd", "")
                            break
                        except Exception:
                            continue
                    if pwd_str is None:
                        # Last resort: decode as latin-1 and replace invalid chars
                        pwd_str = pwd.decode("latin-1", errors="replace")
                else:
                    # If string, ensure it's valid UTF-8
                    pwd_str = str(pwd)
                    try:
                        # Clean any invalid UTF-8 sequences
                        pwd_bytes = pwd_str.encode("utf-8", errors="replace")
                        pwd_str = pwd_bytes.decode("utf-8", errors="replace")
                        # Remove replacement characters
                        pwd_str = pwd_str.replace("\ufffd", "")
                    except Exception:
                        # If encoding fails, try to clean manually
                        pwd_str = "".join(c for c in pwd_str if ord(c) < 0x110000)

                # Clean other string parameters too
                clean_host = str(settings.POSTGRES_HOST).encode("utf-8", errors="replace").decode("utf-8", errors="replace")
                clean_user = str(settings.POSTGRES_USER).encode("utf-8", errors="replace").decode("utf-8", errors="replace")
                clean_db = str(settings.POSTGRES_DB).encode("utf-8", errors="replace").decode("utf-8", errors="replace")

                # Use a completely clean URL without any special characters
                # Use localhost as placeholder - all real params come from connect_args
                minimal_url = "postgresql+psycopg2://localhost/postgres"

                # Create a custom connection creator that builds DSN directly
                # This completely bypasses URL parsing in psycopg2
                def create_connection():
                    import psycopg2
                    # Build DSN string directly with cleaned values
                    dsn_parts = [
                        f"host={clean_host}",
                        f"port={settings.POSTGRES_PORT}",
                        f"user={clean_user}",
                        f"password={pwd_str}",
                        f"dbname={clean_db}",
                        "client_encoding=utf8"
                    ]
                    dsn = " ".join(dsn_parts)
                    return psycopg2.connect(dsn)

                connectable = create_engine(
                    minimal_url,
                    poolclass=pool.NullPool,
                    echo=False,
                    future=True,
                    creator=create_connection,  # Use custom connection creator
                )
                # Test the connection
                with connectable.connect() as test_conn:
                    test_conn.execute(text("SELECT 1"))
            except Exception as e2:
                print(
                    "\n❌ Error: Could not create database connection due to encoding issues",
                    file=sys.stderr
                )
                print(
                    "This usually means the password or connection string has encoding issues.",
                    file=sys.stderr
                )
                print(
                    "Please check your .env file is saved as UTF-8 encoding.",
                    file=sys.stderr
                )
                print(
                    "If your password contains special characters, try URL-encoding them manually.",
                    file=sys.stderr
                )
                raise e2
        else:
            # Not an encoding error, re-raise the original exception
            raise

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

