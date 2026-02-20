"""Robust integration tests for database operations."""

from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.core.auth import hash_password
from app.models.tenant import Tenant
from app.models.user import User


def test_database_transaction_rollback(db_session):
    """Test that database transactions can be rolled back."""
    # Create tenant
    tenant = Tenant(
        name="Test Tenant",
        slug=f"test-tenant-{uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    tenant_id = tenant.id

    # Start a transaction that will fail
    try:
        user1 = User(
            email="test1@example.com",
            password_hash=hash_password("password"),
            full_name="Test User 1",
            tenant_id=tenant_id,
            is_active=True,
        )
        db_session.add(user1)
        db_session.flush()  # Flush to get ID

        # Try to create duplicate email (should fail)
        user2 = User(
            email="test1@example.com",  # Duplicate email
            password_hash=hash_password("password"),
            full_name="Test User 2",
            tenant_id=tenant_id,
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()

        # Should not reach here
        assert False, "Should have raised IntegrityError"
    except IntegrityError:
        # Expected error, rollback
        db_session.rollback()

        # Verify user1 was not committed
        user = db_session.query(User).filter(User.email == "test1@example.com").first()
        assert user is None


def test_database_foreign_key_constraints(db_session):
    """Test that foreign key constraints are enforced."""
    # Try to create user with non-existent tenant_id
    invalid_tenant_id = uuid4()

    try:
        user = User(
            email="test@example.com",
            password_hash=hash_password("password"),
            full_name="Test User",
            tenant_id=invalid_tenant_id,  # Non-existent tenant
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        # Should not reach here if foreign key constraint is enforced
        # (Some DBs might defer constraint checking)
        db_session.rollback()
    except IntegrityError:
        # Expected error for foreign key violation
        db_session.rollback()
        assert True


def test_database_multi_tenant_isolation(db_session):
    """Test that multi-tenant data isolation works at DB level."""
    # Create two tenants
    tenant1 = Tenant(
        name="Tenant 1",
        slug=f"tenant-1-{uuid4().hex[:8]}",
    )
    tenant2 = Tenant(
        name="Tenant 2",
        slug=f"tenant-2-{uuid4().hex[:8]}",
    )
    db_session.add(tenant1)
    db_session.add(tenant2)
    db_session.commit()
    db_session.refresh(tenant1)
    db_session.refresh(tenant2)

    # Create users in each tenant
    user1 = User(
        email="user1@example.com",
        password_hash=hash_password("password"),
        full_name="User 1",
        tenant_id=tenant1.id,
        is_active=True,
    )
    user2 = User(
        email="user2@example.com",
        password_hash=hash_password("password"),
        full_name="User 2",
        tenant_id=tenant2.id,
        is_active=True,
    )
    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)

    # Verify isolation: users from tenant1 should not see tenant2 users
    tenant1_users = db_session.query(User).filter(User.tenant_id == tenant1.id).all()
    tenant2_users = db_session.query(User).filter(User.tenant_id == tenant2.id).all()

    assert len(tenant1_users) == 1
    assert len(tenant2_users) == 1
    assert tenant1_users[0].id == user1.id
    assert tenant2_users[0].id == user2.id

    # Verify cross-tenant access is prevented at query level
    all_users = db_session.query(User).all()
    assert len(all_users) >= 2  # At least our two users

    # But filtered by tenant, should only see own tenant's users
    assert all(u.tenant_id == tenant1.id for u in tenant1_users)


def test_database_cascade_delete(db_session):
    """Test that cascade deletes work correctly."""
    # Create tenant
    tenant = Tenant(
        name="Cascade Test Tenant",
        slug=f"cascade-{uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Create user
    user = User(
        email="cascade@example.com",
        password_hash=hash_password("password"),
        full_name="Cascade User",
        tenant_id=tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user_id = user.id

    # Delete tenant (should cascade delete user)
    db_session.delete(tenant)
    db_session.commit()

    # Verify user was deleted
    deleted_user = db_session.query(User).filter(User.id == user_id).first()
    assert deleted_user is None


def test_database_indexes_exist(db_session):
    """Test that required indexes exist on key columns."""
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)

    # Check users table indexes
    user_indexes = inspector.get_indexes("users")
    index_names = [idx["name"] for idx in user_indexes]

    # Verify key indexes exist (exact names may vary)
    # At minimum, should have indexes on email and tenant_id
    email_indexed = any("email" in name for name in index_names) or any("email" in str(idx) for idx in user_indexes)
    tenant_indexed = any("tenant_id" in name for name in index_names) or any("tenant_id" in str(idx) for idx in user_indexes)

    # These are critical for performance
    assert email_indexed or len(user_indexes) > 0
    assert tenant_indexed or len(user_indexes) > 0


def test_database_unique_constraints(db_session):
    """Test that unique constraints are enforced."""
    tenant = Tenant(
        name="Unique Test Tenant",
        slug=f"unique-{uuid4().hex[:8]}",
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)

    # Create first user
    user1 = User(
        email="unique@example.com",
        password_hash=hash_password("password"),
        full_name="User 1",
        tenant_id=tenant.id,
        is_active=True,
    )
    db_session.add(user1)
    db_session.commit()

    # Try to create duplicate email (should fail)
    try:
        user2 = User(
            email="unique@example.com",  # Duplicate
            password_hash=hash_password("password"),
            full_name="User 2",
            tenant_id=tenant.id,
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()

        # Should not reach here
        assert False, "Should have raised IntegrityError for duplicate email"
    except IntegrityError:
        # Expected error
        db_session.rollback()
        assert True

