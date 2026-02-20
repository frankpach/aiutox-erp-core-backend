"""Condition evaluator for automation rules."""

import logging
from typing import Any

from app.core.pubsub.models import Event

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluator for rule conditions."""

    def evaluate(self, conditions: list[dict[str, Any]], event: Event) -> bool:
        """Evaluate conditions against an event.

        Args:
            conditions: List of condition dictionaries
            event: Event to evaluate against

        Returns:
            True if all conditions are met, False otherwise
        """
        if not conditions:
            return True

        for condition in conditions:
            if not self._evaluate_condition(condition, event):
                return False

        return True

    def _evaluate_condition(self, condition: dict[str, Any], event: Event) -> bool:
        """Evaluate a single condition.

        Args:
            condition: Condition dictionary with 'field', 'operator', 'value'
            event: Event to evaluate against

        Returns:
            True if condition is met, False otherwise
        """
        field_path = condition.get("field", "")
        operator = condition.get("operator", "==")
        expected_value = condition.get("value")

        # Get value from event using field path
        actual_value = self._get_field_value(event, field_path)

        # Evaluate based on operator
        try:
            if operator == "==":
                return actual_value == expected_value
            elif operator == "!=":
                return actual_value != expected_value
            elif operator == ">":
                return actual_value > expected_value
            elif operator == "<":
                return actual_value < expected_value
            elif operator == ">=":
                return actual_value >= expected_value
            elif operator == "<=":
                return actual_value <= expected_value
            elif operator == "in":
                return (
                    actual_value in expected_value
                    if isinstance(expected_value, (list, tuple))
                    else False
                )
            elif operator == "contains":
                if isinstance(actual_value, str) and isinstance(expected_value, str):
                    return expected_value in actual_value
                if isinstance(actual_value, (list, tuple)):
                    return expected_value in actual_value
                return False
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
        except (TypeError, ValueError) as e:
            logger.warning(f"Error evaluating condition {condition}: {e}")
            return False

    def _get_field_value(self, event: Event, field_path: str) -> Any:
        """Get value from event using field path.

        Args:
            event: Event object
            field_path: Dot-separated field path (e.g., 'metadata.additional_data.stock.quantity')

        Returns:
            Field value or None if not found
        """
        if not field_path:
            return None

        parts = field_path.split(".")
        value: Any = event

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        return value
