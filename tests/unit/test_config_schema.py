"""Unit tests for ConfigSchema validation."""

import pytest

from app.core.config.schema import ConfigSchema


class TestConfigSchema:
    """Test suite for ConfigSchema validation."""

    def test_validate_string_type(self):
        """Test string type validation."""
        schema = ConfigSchema()
        schema.register_schema("test", "name", {"type": "string"})

        assert schema.validate("test", "name", "valid") is True
        assert schema.validate("test", "name", 123) is False
        assert schema.validate("test", "name", True) is False

    def test_validate_int_type(self):
        """Test integer type validation."""
        schema = ConfigSchema()
        schema.register_schema("test", "count", {"type": "int"})

        assert schema.validate("test", "count", 10) is True
        assert schema.validate("test", "count", "10") is False
        assert schema.validate("test", "count", 10.5) is False
        assert schema.validate("test", "count", True) is False  # bool is not int

    def test_validate_float_type(self):
        """Test float type validation."""
        schema = ConfigSchema()
        schema.register_schema("test", "price", {"type": "float"})

        assert schema.validate("test", "price", 10.5) is True
        assert schema.validate("test", "price", 10) is True  # int acceptable
        assert schema.validate("test", "price", "10.5") is False
        assert schema.validate("test", "price", True) is False  # bool is not float

    def test_validate_bool_type(self):
        """Test boolean type validation."""
        schema = ConfigSchema()
        schema.register_schema("test", "enabled", {"type": "bool"})

        assert schema.validate("test", "enabled", True) is True
        assert schema.validate("test", "enabled", False) is True
        assert schema.validate("test", "enabled", 1) is False
        assert schema.validate("test", "enabled", "true") is False

    def test_validate_dict_type(self):
        """Test dictionary type validation."""
        schema = ConfigSchema()
        schema.register_schema("test", "settings", {"type": "dict"})

        assert schema.validate("test", "settings", {"key": "value"}) is True
        assert schema.validate("test", "settings", {}) is True
        assert schema.validate("test", "settings", []) is False
        assert schema.validate("test", "settings", "dict") is False

    def test_validate_list_type(self):
        """Test list type validation."""
        schema = ConfigSchema()
        schema.register_schema("test", "items", {"type": "list"})

        assert schema.validate("test", "items", [1, 2, 3]) is True
        assert schema.validate("test", "items", []) is True
        assert schema.validate("test", "items", {}) is False
        assert schema.validate("test", "items", "list") is False

    def test_validate_pattern_hex_color(self):
        """Test pattern validation for hex colors."""
        schema = ConfigSchema()
        schema.register_schema(
            "app_theme",
            "primary_color",
            {"type": "string", "pattern": r"^#[0-9A-Fa-f]{6}$"}
        )

        # Valid colors
        assert schema.validate("app_theme", "primary_color", "#1976D2") is True
        assert schema.validate("app_theme", "primary_color", "#FFFFFF") is True
        assert schema.validate("app_theme", "primary_color", "#000000") is True
        assert schema.validate("app_theme", "primary_color", "#abc123") is True

        # Invalid colors
        assert schema.validate("app_theme", "primary_color", "blue") is False
        assert schema.validate("app_theme", "primary_color", "#GGG") is False
        assert schema.validate("app_theme", "primary_color", "#12345") is False
        assert schema.validate("app_theme", "primary_color", "#1234567") is False
        assert schema.validate("app_theme", "primary_color", "1976D2") is False

    def test_validate_enum(self):
        """Test enum validation."""
        schema = ConfigSchema()
        schema.register_schema(
            "products",
            "currency",
            {"type": "string", "enum": ["USD", "EUR", "GBP"]}
        )

        assert schema.validate("products", "currency", "USD") is True
        assert schema.validate("products", "currency", "EUR") is True
        assert schema.validate("products", "currency", "GBP") is True
        assert schema.validate("products", "currency", "JPY") is False
        assert schema.validate("products", "currency", "usd") is False

    def test_validate_min_max_range(self):
        """Test min/max range validation for numbers."""
        schema = ConfigSchema()
        schema.register_schema(
            "products",
            "discount",
            {"type": "float", "min": 0.0, "max": 100.0}
        )

        # Valid values
        assert schema.validate("products", "discount", 0.0) is True
        assert schema.validate("products", "discount", 50.0) is True
        assert schema.validate("products", "discount", 100.0) is True

        # Invalid values
        assert schema.validate("products", "discount", -1.0) is False
        assert schema.validate("products", "discount", 101.0) is False

    def test_validate_min_length(self):
        """Test minLength validation for strings."""
        schema = ConfigSchema()
        schema.register_schema(
            "auth",
            "password",
            {"type": "string", "minLength": 8}
        )

        assert schema.validate("auth", "password", "12345678") is True
        assert schema.validate("auth", "password", "verylongpassword") is True
        assert schema.validate("auth", "password", "1234567") is False
        assert schema.validate("auth", "password", "") is False

    def test_validate_max_length(self):
        """Test maxLength validation for strings."""
        schema = ConfigSchema()
        schema.register_schema(
            "users",
            "username",
            {"type": "string", "maxLength": 20}
        )

        assert schema.validate("users", "username", "user") is True
        assert schema.validate("users", "username", "a" * 20) is True
        assert schema.validate("users", "username", "a" * 21) is False

    def test_validate_combined_validations(self):
        """Test combining multiple validation rules."""
        schema = ConfigSchema()
        schema.register_schema(
            "products",
            "sku",
            {
                "type": "string",
                "pattern": r"^[A-Z]{2}\d{6}$",
                "minLength": 8,
                "maxLength": 8
            }
        )

        # Valid SKU
        assert schema.validate("products", "sku", "AB123456") is True

        # Invalid cases
        assert schema.validate("products", "sku", "ab123456") is False  # lowercase
        assert schema.validate("products", "sku", "A123456") is False  # too short
        assert schema.validate("products", "sku", "ABC123456") is False  # too long
        assert schema.validate("products", "sku", "ABCDEFGH") is False  # no digits

    def test_validate_no_schema_registered(self):
        """Test that validation passes when no schema is registered."""
        schema = ConfigSchema()

        # Any value should be valid without a schema
        assert schema.validate("unknown", "key", "any value") is True
        assert schema.validate("unknown", "key", 123) is True
        assert schema.validate("unknown", "key", True) is True
        assert schema.validate("unknown", "key", {"nested": "dict"}) is True

    def test_get_default_value(self):
        """Test getting default value from schema."""
        schema = ConfigSchema()
        schema.register_schema(
            "products",
            "min_price",
            {"type": "float", "default": 0.0}
        )

        assert schema.get_default("products", "min_price") == 0.0

    def test_get_default_no_default(self):
        """Test getting default when none is defined."""
        schema = ConfigSchema()
        schema.register_schema(
            "products",
            "name",
            {"type": "string"}
        )

        assert schema.get_default("products", "name") is None

    def test_get_default_no_schema(self):
        """Test getting default for non-existent schema."""
        schema = ConfigSchema()

        assert schema.get_default("unknown", "key") is None

    def test_wildcard_pattern_validation(self):
        """Test wildcard pattern matching."""
        schema = ConfigSchema()
        schema.register_schema(
            "system",
            "modules.*.enabled",
            {"type": "bool", "default": True}
        )

        # Should match any module name
        assert schema.validate("system", "modules.products.enabled", True) is True
        assert schema.validate("system", "modules.inventory.enabled", False) is True
        assert schema.validate("system", "modules.sales.enabled", "yes") is False  # wrong type


















