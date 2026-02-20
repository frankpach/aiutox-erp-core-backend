"""Configuration for comment module tests."""

from uuid import uuid4

import pytest
from app.core.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.task import Task
from app.models.user import User
from app.modules.products.models.product import Product

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session."""
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_tenant():
    """Test tenant ID."""
    return uuid4()


@pytest.fixture
def test_user(test_db, test_tenant):
    """Create test user."""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant,
        email="test@example.com",
        full_name="Test User",
        is_active=True,
    )
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def test_task(test_db, test_tenant, test_user):
    """Create test task."""
    task = Task(
        id=uuid4(),
        tenant_id=test_tenant,
        title="Test Task",
        description="Test task description",
        created_by_id=test_user.id,
    )
    test_db.add(task)
    test_db.commit()
    return task


@pytest.fixture
def test_product(test_db, test_tenant, test_user):
    """Create test product."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant,
        name="Test Product",
        description="Test product description",
        sku="TEST-001",
        created_by_id=test_user.id,
    )
    test_db.add(product)
    test_db.commit()
    return product


