from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.auth import create_access_token, hash_password
from app.core.config_file import get_settings
from app.core.db.deps import get_db
from app.core.db.session import Base
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole

settings = get_settings()

# Create test database
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/aiutox_erp_dev", "/aiutox_erp_test"
)

# Print connection info for debugging
print(f"\n[DB CONNECTION] Test Database Connection Info:")
# Mask password in URL for security
if "@" in TEST_DATABASE_URL:
    parts = TEST_DATABASE_URL.split("@")
    if "://" in parts[0]:
        protocol_user = parts[0].split("://")[0] + "://"
        user_pass = parts[0].split("://")[1]
        if ":" in user_pass:
            user = user_pass.split(":")[0]
            masked_url = f"{protocol_user}{user}:***@{parts[1]}"
        else:
            masked_url = TEST_DATABASE_URL
    else:
        masked_url = TEST_DATABASE_URL
else:
    masked_url = TEST_DATABASE_URL

print(f"   URL (masked): {masked_url}")
print(f"   Host: {settings.POSTGRES_HOST}")
print(f"   Port: {settings.POSTGRES_PORT}")
print(f"   Database: {TEST_DATABASE_URL.split('/')[-1]}")
print(f"   User: {settings.POSTGRES_USER}")
print(f"   Password length: {len(settings.POSTGRES_PASSWORD)}")
print(f"   Password (first 3 chars): {settings.POSTGRES_PASSWORD[:3]}...")
print(f"   Full DATABASE_URL length: {len(settings.DATABASE_URL)}")
print(f"   Full TEST_DATABASE_URL length: {len(TEST_DATABASE_URL)}")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


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
    db_session.commit()
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
    db_session.commit()
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
    db_session.commit()
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
    db_session.commit()
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
    """Register custom markers."""
    config.addinivalue_line("markers", "redis: mark test as requiring Redis")
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is available for integration tests."""
    import asyncio

    async def check_redis():
        try:
            from app.core.pubsub.client import RedisStreamsClient

            client = RedisStreamsClient(
                redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD
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
