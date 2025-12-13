"""Rule parser for automation rules."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RuleParser:
    """Parser for automation rules from JSON/YAML."""

    @staticmethod
    def parse(rule_definition: dict[str, Any]) -> dict[str, Any]:
        """Parse a rule definition.

        Args:
            rule_definition: Rule definition dictionary

        Returns:
            Parsed rule dictionary

        Raises:
            ValueError: If rule definition is invalid
        """
        # Validate required fields
        required_fields = ["name", "trigger", "actions"]
        for field in required_fields:
            if field not in rule_definition:
                raise ValueError(f"Missing required field: {field}")

        # Validate trigger
        trigger = rule_definition.get("trigger", {})
        if not isinstance(trigger, dict):
            raise ValueError("trigger must be a dictionary")
        if "type" not in trigger:
            raise ValueError("trigger must have a 'type' field")

        trigger_type = trigger.get("type")
        if trigger_type == "event":
            if "event_type" not in trigger:
                raise ValueError("event trigger must have 'event_type' field")
        elif trigger_type == "time":
            if "schedule" not in trigger:
                raise ValueError("time trigger must have 'schedule' field")
        else:
            raise ValueError(f"Unknown trigger type: {trigger_type}")

        # Validate actions
        actions = rule_definition.get("actions", [])
        if not isinstance(actions, list) or len(actions) == 0:
            raise ValueError("actions must be a non-empty list")

        for action in actions:
            if not isinstance(action, dict):
                raise ValueError("Each action must be a dictionary")
            if "type" not in action:
                raise ValueError("Each action must have a 'type' field")

        # Validate conditions (optional)
        conditions = rule_definition.get("conditions")
        if conditions is not None:
            if not isinstance(conditions, list):
                raise ValueError("conditions must be a list")
            for condition in conditions:
                if not isinstance(condition, dict):
                    raise ValueError("Each condition must be a dictionary")
                required_condition_fields = ["field", "operator", "value"]
                for field in required_condition_fields:
                    if field not in condition:
                        raise ValueError(f"Condition missing required field: {field}")

        return {
            "name": rule_definition["name"],
            "description": rule_definition.get("description"),
            "enabled": rule_definition.get("enabled", True),
            "trigger": trigger,
            "conditions": conditions or [],
            "actions": actions,
        }

    @staticmethod
    def validate(rule_definition: dict[str, Any]) -> bool:
        """Validate a rule definition.

        Args:
            rule_definition: Rule definition dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            RuleParser.parse(rule_definition)
            return True
        except (ValueError, KeyError, TypeError) as e:
            logger.warning(f"Invalid rule definition: {e}")
            return False



