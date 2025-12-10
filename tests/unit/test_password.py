"""Unit tests for password hashing and verification utilities."""

import pytest

from app.core.auth.password import hash_password, verify_password


def test_hash_password_generates_different_strings():
    """Test that hash_password generates different strings each time."""
    password = "test_password_123"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    # Each hash should be different (bcrypt includes salt)
    assert hash1 != hash2
    # But both should be valid hashes (non-empty strings)
    assert len(hash1) > 0
    assert len(hash2) > 0


def test_verify_password_correct():
    """Test that verify_password returns True for correct password."""
    password = "test_password_123"
    hashed = hash_password(password)

    result = verify_password(password, hashed)
    assert result is True


def test_verify_password_incorrect():
    """Test that verify_password returns False for incorrect password."""
    password = "test_password_123"
    wrong_password = "wrong_password"
    hashed = hash_password(password)

    result = verify_password(wrong_password, hashed)
    assert result is False


def test_hash_password_bcrypt_cost():
    """Test that hash_password uses bcrypt with cost factor 12."""
    password = "test_password_123"
    hashed = hash_password(password)

    # bcrypt hashes start with $2b$ or $2a$ or $2y$
    assert hashed.startswith("$2")
    # Extract cost factor from hash (format: $2b$XX$...)
    parts = hashed.split("$")
    assert len(parts) >= 4
    # Cost factor is in the third part (index 2)
    cost_factor = int(parts[2])
    assert cost_factor >= 12, f"Expected cost factor >= 12, got {cost_factor}"


def test_hash_password_empty_string():
    """Test that hash_password handles empty string."""
    hashed = hash_password("")
    assert len(hashed) > 0
    assert verify_password("", hashed) is True


def test_verify_password_empty_string():
    """Test that verify_password handles empty string correctly."""
    password = "test_password"
    hashed = hash_password(password)

    # Empty string should not verify against non-empty password
    assert verify_password("", hashed) is False


def test_hash_password_special_characters():
    """Test that hash_password handles special characters."""
    password = "test!@#$%^&*()_+-=[]{}|;:,.<>?"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrong", hashed) is False



