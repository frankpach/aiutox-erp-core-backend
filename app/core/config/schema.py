"""Schema validation for system configuration."""

from typing import Any


class ConfigSchema:
    """Schema validator for module configurations."""

    def __init__(self):
        """Initialize schema registry."""
        # Registry of schemas by module
        # Format: {module: {key: {type: str, default: Any, required: bool}}}
        self._schemas: dict[str, dict[str, dict[str, Any]]] = {}

    def register_schema(
        self, module: str, key: str, schema_def: dict[str, Any]
    ) -> None:
        """Register a schema definition for a module key.

        Args:
            module: Module name (e.g., 'products', 'inventory')
            key: Configuration key
            schema_def: Schema definition with 'type', 'default', 'required'
        """
        if module not in self._schemas:
            self._schemas[module] = {}
        self._schemas[module][key] = schema_def

    def validate(self, module: str, key: str, value: Any) -> bool:
        """Validate a configuration value against its schema.

        Args:
            module: Module name
            key: Configuration key
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        # Check for exact match first
        if module in self._schemas and key in self._schemas[module]:
            schema_def = self._schemas[module][key]
        # Check for wildcard patterns (e.g., "modules.*.enabled")
        elif module in self._schemas:
            # Look for wildcard patterns
            for pattern_key, schema_def in self._schemas[module].items():
                if "*" in pattern_key:
                    # Simple wildcard matching: replace * with .* for regex-like matching
                    import re
                    pattern = pattern_key.replace("*", ".*")
                    if re.match(pattern, key):
                        break
            else:
                # No pattern matched, allow any value
                return True
        else:
            # No schema registered, allow any value
            return True

        expected_type = schema_def.get("type", "any")

        # Type validation
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "int":
            return isinstance(value, int)
        elif expected_type == "float":
            return isinstance(value, (int, float))
        elif expected_type == "bool":
            return isinstance(value, bool)
        elif expected_type == "dict":
            return isinstance(value, dict)
        elif expected_type == "list":
            return isinstance(value, list)
        elif expected_type == "any":
            return True
        else:
            # Unknown type, allow it
            return True

    def get_default(self, module: str, key: str) -> Any:
        """Get default value for a configuration key.

        Args:
            module: Module name
            key: Configuration key

        Returns:
            Default value or None
        """
        # Check for exact match first
        if module in self._schemas and key in self._schemas[module]:
            schema_def = self._schemas[module][key]
            if "default" in schema_def:
                return schema_def["default"]

        # Check for wildcard patterns
        if module in self._schemas:
            import re
            for pattern_key, schema_def in self._schemas[module].items():
                if "*" in pattern_key:
                    pattern = pattern_key.replace("*", ".*")
                    if re.match(pattern, key) and "default" in schema_def:
                        return schema_def["default"]

        return None


# Global instance
config_schema = ConfigSchema()


def register_module_schemas() -> None:
    """Register schemas for module management in the system module.

    This registers the schema for system.modules.{module_id}.enabled
    which allows enabling/disabling modules via the configuration system.
    """
    # Register schema for module enable/disable
    # Note: The key pattern is "modules.{module_id}.enabled"
    # We register a generic pattern that will match any module_id
    # The validation will accept any module_id in the key
    config_schema.register_schema(
        module="system",
        key="modules.*.enabled",  # Wildcard pattern for any module
        schema_def={
            "type": "bool",
            "default": True,
            "required": False,
            "description": "Enable/disable a module",
        },
    )


# Auto-register module schemas on import
register_module_schemas()



