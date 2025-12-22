import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.auth import create_access_token, hash_password
from app.core.config_file import get_settings
from app.core.db.deps import get_db
from app.core.db.session import Base
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole

# Load environment variables from .env files
# Priority: .env (current dir) > ../.env (parent dir) > system env vars
backend_dir = Path(__file__).parent.parent
env_files = [
    backend_dir / ".env",  # backend/.env
    backend_dir.parent / ".env",  # ../.env (project root)
]

# Load .env files (later files override earlier ones)
for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file, override=False)  # Don't override existing env vars
        print(f"[TEST CONFIG] Loaded environment from: {env_file}")

# Clear settings cache to force reload with new env vars
get_settings.cache_clear()

# Get settings after loading .env files
settings = get_settings()

# Determine test database URL
# Priority: Use environment variables > settings from .env > fallback defaults
def get_test_database_url():
    """Get test database URL with proper fallbacks."""
    # Check for explicit test database URL in environment
    test_db_url_env = os.getenv("TEST_DATABASE_URL")
    if test_db_url_env:
        return test_db_url_env

    # Get base database URL from settings
    base_db_url = settings.database_url

    # For tests, we typically run outside Docker, so convert Docker hostnames to localhost
    # Check if URL contains Docker hostname 'db'
    if "db:" in base_db_url or "@db:" in base_db_url:
        # Replace Docker hostname with localhost and use mapped port
        # Handle both formats: @db:5432 and db:5432
        test_db_url = base_db_url.replace("@db:5432", "@localhost:15432")
        test_db_url = test_db_url.replace("db:5432", "localhost:15432")
        # Also handle if port is not specified or different
        test_db_url = test_db_url.replace("@db/", "@localhost:15432/")
        test_db_url = test_db_url.replace("db/", "localhost:15432/")
    elif settings.POSTGRES_HOST == "db" and settings.POSTGRES_PORT == 5432:
        # If using Docker hostname/port in components, override to localhost:15432
        test_db_url = (
            f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@localhost:15432/{settings.POSTGRES_DB}"
        )
    else:
        # Use settings as-is, but ensure we're using the right host/port
        # If host is 'db', convert to localhost:15432
        if settings.POSTGRES_HOST == "db":
            test_db_url = (
                f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@localhost:15432/{settings.POSTGRES_DB}"
            )
        else:
            # Use settings URL directly
            test_db_url = base_db_url

    return test_db_url

test_db_url = get_test_database_url()

# Support for pytest-xdist workers: use separate database per worker
def get_test_database_name():
    """Get test database name, with worker-specific suffix if using pytest-xdist."""
    base_name = os.getenv("TEST_POSTGRES_DB", "aiutox_erp_test")
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")

    if worker_id and worker_id != "master":
        # Use worker-specific database name
        db_name = f"{base_name}_{worker_id}"
        print(f"[TEST CONFIG] Using worker-specific database: {db_name} (worker: {worker_id})")
        return db_name

    return base_name

TEST_DB_NAME = get_test_database_name()

# Replace database name in URL
if "/" in test_db_url:
    # Extract base URL (everything before the last /)
    base_url = test_db_url.rsplit("/", 1)[0]
    TEST_DATABASE_URL = f"{base_url}/{TEST_DB_NAME}"
else:
    # Fallback: try to replace common database names
    TEST_DATABASE_URL = test_db_url.replace("/aiutox_erp_dev", f"/{TEST_DB_NAME}")
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("/postgres", f"/{TEST_DB_NAME}")

# Print connection info for debugging
def mask_password_in_url(url: str) -> str:
    """Mask password in database URL for secure logging."""
    if "@" not in url:
        return url
    parts = url.split("@")
    if "://" in parts[0]:
        protocol_user = parts[0].split("://")[0] + "://"
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            return f"{protocol_user}{user}:***@{parts[1]}"
    return url

print(f"\n[TEST CONFIG] Test Database Configuration:")
print(f"   Source: .env files loaded from: {[str(f) for f in env_files if f.exists()]}")
print(f"   URL (masked): {mask_password_in_url(TEST_DATABASE_URL)}")
print(f"   Base URL (masked): {mask_password_in_url(test_db_url)}")
print(f"   Host: {settings.POSTGRES_HOST}")
print(f"   Port: {settings.POSTGRES_PORT}")
print(f"   Database: {TEST_DB_NAME}")
print(f"   User: {settings.POSTGRES_USER}")
print(f"   DATABASE_URL from env: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")
print(f"   TEST_DATABASE_URL from env: {os.getenv('TEST_DATABASE_URL', 'Not set')}")

# Create test database if it doesn't exist (for tests running outside Docker)
# Extract connection info for admin database
admin_db_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
try:
    admin_engine = create_engine(admin_db_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
    with admin_engine.connect() as conn:
        # Check if test database exists
        result = conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
        )
        if result.fetchone():
            # Database exists - drop it with FORCE to disconnect all sessions
            print(f"   [DB] Test database '{TEST_DB_NAME}' already exists, dropping with FORCE...")
            try:
                # Terminate all connections to the database first
                conn.execute(
                    text(f"""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
                    AND pid <> pg_backend_pid();
                    """)
                )
                # Now drop the database
                conn.execute(text(f"DROP DATABASE {TEST_DB_NAME}"))
                print(f"   [DB] Dropped existing test database '{TEST_DB_NAME}'")
            except Exception as drop_error:
                print(f"   [DB WARNING] Could not drop existing database: {drop_error}")
                # Try to continue anyway - might work if no connections

        # Create test database
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
        print(f"   [DB] Created test database '{TEST_DB_NAME}'")
    admin_engine.dispose()
except Exception as e:
    print(f"   [DB WARNING] Could not create test database (may already exist or not accessible): {e}")
    print(f"   [DB WARNING] Attempted connection to: {mask_password_in_url(admin_db_url)}")

# Store original TEST_DATABASE_URL for use in fixtures
_ORIGINAL_TEST_DATABASE_URL = TEST_DATABASE_URL

# Create engine with proper connection settings for tests
# This will be recreated per worker if needed
def create_test_engine(database_url: str = None):
    """Create test database engine."""
    url = database_url or TEST_DATABASE_URL
    return create_engine(
        url,
        pool_pre_ping=True,  # Verify connections before using
        connect_args={
            "connect_timeout": 5,  # 5 second timeout
            "options": "-c timezone=utc"
        }
    )

engine = create_test_engine()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def setup_database():
    """Setup database using Alembic migrations (runs once per test session).

    This fixture:
    1. Creates all tables using Alembic migrations (core + modules)
    2. Ensures proper order of table creation (respects foreign key dependencies)
    3. Handles custom PostgreSQL types correctly
    4. Runs once per session for performance
    """
    from app.core.migrations.manager import MigrationManager
    from alembic import config as alembic_config

    print(f"\n[TEST SETUP] Setting up database with migrations...")
    print(f"   Database: {TEST_DB_NAME}")
    print(f"   URL (masked): {mask_password_in_url(TEST_DATABASE_URL)}")

    # Create engine for migrations (use the test database URL)
    migration_engine = create_test_engine()

    try:
        # Use MigrationManager to apply all migrations
        # This ensures all tables (core + modules) are created in correct order
        manager = MigrationManager()

        # Override engine to use test database
        manager.engine = migration_engine

        # Update Alembic config to use test database URL
        # This ensures Alembic commands use the correct database
        # IMPORTANT: This must be done before any Alembic operations
        manager.alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

        # Also update the settings in env.py context (if it reads from settings)
        # The env.py file reads from get_settings(), but we override the config URL
        # which takes precedence in Alembic operations

        # Apply all migrations
        result = manager.apply_migrations()

        if not result.success:
            error_msg = f"Failed to setup test database: {result.errors}"
            print(f"   [ERROR] {error_msg}")
            raise RuntimeError(error_msg)

        applied_count = len(result.applied) if hasattr(result, 'applied') else result.applied_count
        print(f"   [SUCCESS] Database setup complete ({applied_count} migrations applied)")

        yield

    finally:
        # Optional: Clean up at end of session
        # For now, we leave the database intact for faster subsequent runs
        migration_engine.dispose()


@pytest.fixture(scope="function")
def db_session(setup_database):
    """Create an isolated database session using transactions for each test.

    Each test runs in its own transaction that is rolled back at the end,
    ensuring complete isolation between tests without needing to clean data.
    """
    # Create a new connection and transaction for this test
    connection = engine.connect()
    transaction = connection.begin()

    # Create session bound to this connection/transaction
    db = TestingSessionLocal(bind=connection)

    try:
        yield db
    finally:
        # Rollback transaction to undo all changes made during the test
        # This provides complete isolation without needing to clean data
        try:
            db.rollback()
        except Exception as e:
            # Session rollback might fail if already closed
            if "already deassociated" not in str(e).lower():
                print(f"[DB CLEANUP] Warning during session rollback: {e}")

        try:
            if transaction.is_active:
                transaction.rollback()
        except Exception as e:
            # Transaction rollback might fail if already deassociated
            if "already deassociated" not in str(e).lower():
                print(f"[DB CLEANUP] Warning during transaction rollback: {e}")
        finally:
            try:
                db.close()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_tenant(db_session):
    """Create a test tenant."""
    tenant = Tenant(
        name="Test Tenant",
        slug=f"test-tenant-{uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.flush()  # Use flush instead of commit (transaction will be rolled back)
    db_session.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
def test_user(db_session, test_tenant):
    """Create a test user with known password."""
    password = "test_password_123"
    password_hash = hash_password(password)

    user = User(
        email=f"test-{uuid4().hex[:8]}@example.com",
        password_hash=password_hash,
        full_name="Test User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()  # Use flush instead of commit (transaction will be rolled back)
    db_session.refresh(user)

    # Store plain password for tests
    user._plain_password = password  # type: ignore
    return user


@pytest.fixture(scope="function")
def test_user_inactive(db_session, test_tenant):
    """Create an inactive test user."""
    password = "test_password_123"
    password_hash = hash_password(password)

    user = User(
        email=f"inactive-{uuid4().hex[:8]}@example.com",
        password_hash=password_hash,
        full_name="Inactive User",
        tenant_id=test_tenant.id,
        is_active=False,
    )
    db_session.add(user)
    db_session.flush()  # Use flush instead of commit (transaction will be rolled back)
    db_session.refresh(user)

    user._plain_password = password  # type: ignore
    return user


@pytest.fixture(scope="function")
def test_user_with_roles(db_session, test_tenant, test_user):
    """Create a test user with roles assigned."""
    # Assign admin role
    role = UserRole(
        user_id=test_user.id,
        role="admin",
        granted_by=test_user.id,
    )
    db_session.add(role)
    db_session.flush()  # Use flush instead of commit (transaction will be rolled back)
    db_session.refresh(test_user)
    return test_user


@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Create authentication headers with valid token."""
    from app.services.auth_service import AuthService
    from app.core.db.deps import get_db

    # Create token data
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "roles": ["admin"],
        "permissions": [],
    }
    token = create_access_token(token_data)

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clear_rate_limit_state():
    """Clear rate limit state before each test to prevent interference."""
    from app.core.auth.rate_limit import _login_attempts

    _login_attempts.clear()
    yield
    _login_attempts.clear()


# Redis availability check for integration tests
def pytest_configure(config):
    """Register custom markers and configure test database per worker."""
    config.addinivalue_line("markers", "redis: mark test as requiring Redis")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "db: mark test as database test")

    # Configure worker-specific database if using pytest-xdist
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id and worker_id != "master":
        # Update global variables for this worker
        global TEST_DB_NAME, TEST_DATABASE_URL, engine, TestingSessionLocal

        base_name = os.getenv("TEST_POSTGRES_DB", "aiutox_erp_test")
        TEST_DB_NAME = f"{base_name}_{worker_id}"

        # Recreate database URL and engine for this worker
        base_url = _ORIGINAL_TEST_DATABASE_URL.rsplit("/", 1)[0]
        TEST_DATABASE_URL = f"{base_url}/{TEST_DB_NAME}"

        # Create worker-specific database if it doesn't exist (drop first if exists)
        admin_db_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
        try:
            admin_engine = create_engine(admin_db_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
            with admin_engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_NAME}'")
                )
                if result.fetchone():
                    # Database exists - drop it with FORCE
                    print(f"[TEST CONFIG] Worker database '{TEST_DB_NAME}' already exists, dropping with FORCE...")
                    try:
                        # Terminate all connections to the database first
                        conn.execute(
                            text(f"""
                            SELECT pg_terminate_backend(pg_stat_activity.pid)
                            FROM pg_stat_activity
                            WHERE pg_stat_activity.datname = '{TEST_DB_NAME}'
                            AND pid <> pg_backend_pid();
                            """)
                        )
                        # Now drop the database
                        conn.execute(text(f"DROP DATABASE {TEST_DB_NAME}"))
                        print(f"[TEST CONFIG] Dropped existing worker database '{TEST_DB_NAME}'")
                    except Exception as drop_error:
                        print(f"[TEST CONFIG] Warning: Could not drop existing worker database: {drop_error}")

                # Create worker database
                conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
                print(f"[TEST CONFIG] Created worker database '{TEST_DB_NAME}' for worker {worker_id}")
            admin_engine.dispose()
        except Exception as e:
            print(f"[TEST CONFIG] Warning: Could not create worker database: {e}")

        # Recreate engine with worker-specific database
        engine = create_test_engine()
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        print(f"[TEST CONFIG] Worker {worker_id} configured with database: {TEST_DB_NAME}")


@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is available for integration tests."""
    import asyncio

    # Get Redis URL from environment or settings
    redis_url = os.getenv("REDIS_URL") or os.getenv("TEST_REDIS_URL") or settings.REDIS_URL
    redis_password = os.getenv("REDIS_PASSWORD") or settings.REDIS_PASSWORD

    # Convert Docker hostname to localhost for tests
    if "redis:" in redis_url or "@redis:" in redis_url:
        redis_url = redis_url.replace("@redis:6379", "@localhost:6379")
        redis_url = redis_url.replace("redis:6379", "localhost:6379")

    async def check_redis():
        try:
            from app.core.pubsub.client import RedisStreamsClient

            client = RedisStreamsClient(
                redis_url=redis_url, password=redis_password
            )
            # Try to connect with a short timeout
            try:
                # Get client with timeout
                redis_conn = await asyncio.wait_for(client._get_client(), timeout=2.0)
                await asyncio.wait_for(redis_conn.ping(), timeout=1.0)
                await client.close()
                return True
            except (asyncio.TimeoutError, Exception):
                try:
                    await client.close()
                except Exception:
                    pass
                return False
        except Exception:
            return False

    # Run the check
    try:
        return asyncio.run(asyncio.wait_for(check_redis(), timeout=3.0))
    except Exception:
        return False


def pytest_sessionfinish(session, exitstatus):
    """Clean up test databases after all tests complete."""
    # Only clean up if tests passed or if explicitly requested
    cleanup_enabled = os.getenv("CLEANUP_TEST_DB", "false").lower() == "true"

    if not cleanup_enabled:
        print("\n[TEST CLEANUP] Skipping database cleanup (set CLEANUP_TEST_DB=true to enable)")
        return

    print("\n[TEST CLEANUP] Cleaning up test databases...")

    # Get all test database names (base + workers)
    base_name = os.getenv("TEST_POSTGRES_DB", "aiutox_erp_test")
    test_db_names = [base_name]

    # Add worker databases if any
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id and worker_id != "master":
        test_db_names.append(f"{base_name}_{worker_id}")
    else:
        # If not a worker, try to find all worker databases
        admin_db_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
        try:
            admin_engine = create_engine(admin_db_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
            with admin_engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT datname FROM pg_database WHERE datname LIKE '{base_name}_%'")
                )
                for row in result:
                    test_db_names.append(row[0])
            admin_engine.dispose()
        except Exception:
            pass

    # Drop all test databases
    admin_db_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    try:
        admin_engine = create_engine(admin_db_url, isolation_level="AUTOCOMMIT", connect_args={"connect_timeout": 5})
        with admin_engine.connect() as conn:
            for db_name in test_db_names:
                try:
                    # Terminate all connections first
                    conn.execute(
                        text(f"""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = '{db_name}'
                        AND pid <> pg_backend_pid();
                        """)
                    )
                    # Drop database
                    conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
                    print(f"   [CLEANUP] Dropped test database '{db_name}'")
                except Exception as e:
                    print(f"   [CLEANUP WARNING] Could not drop database '{db_name}': {e}")
        admin_engine.dispose()
        print("[TEST CLEANUP] Cleanup complete")
    except Exception as e:
        print(f"[TEST CLEANUP] Could not cleanup databases: {e}")
