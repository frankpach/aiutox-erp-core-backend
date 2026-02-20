"""Test constants for secure testing."""

import secrets
import string


# Generate a secure test password once at module level
# This is more secure than hardcoded "test_password_123"
def generate_test_password(length: int = 16) -> str:
    """Generate a secure test password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# Use a consistent but secure test password
TEST_PASSWORD = generate_test_password()
TEST_USER_EMAIL = "test-user@example.com"

# For backward compatibility during transition
LEGACY_TEST_PASSWORD = "test_password_123"  # Will be removed after migration
