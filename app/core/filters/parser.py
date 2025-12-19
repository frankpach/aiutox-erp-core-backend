"""Filter parser for applying complex filters to SQLAlchemy queries."""

import logging
from typing import Any

from sqlalchemy.orm import Query

logger = logging.getLogger(__name__)


class FilterParser:
    """Parser for applying complex filters to SQLAlchemy queries.

    Supports various operators for filtering data:
    - Comparison: eq, ne, gt, gte, lt, lte
    - Membership: in, not_in
    - Range: between
    - String: contains, starts_with, ends_with (case-insensitive)
    - Null checks: is_null, is_not_null
    """

    @staticmethod
    def apply_filters(query: Query, model_class: type, filters: dict[str, Any]) -> Query:
        """Apply filters to a SQLAlchemy query.

        Args:
            query: SQLAlchemy query object
            model_class: SQLAlchemy model class
            filters: Dictionary of filters in SavedFilter format
                Example: {
                    "status": {"operator": "in", "value": ["active", "pending"]},
                    "price": {"operator": "between", "value": {"min": 100, "max": 500}},
                    "name": {"operator": "contains", "value": "laptop"}
                }

        Returns:
            Query with filters applied
        """
        for field_name, filter_config in filters.items():
            # Skip if field doesn't exist in model
            if not hasattr(model_class, field_name):
                logger.warning(f"Field '{field_name}' not found in model {model_class.__name__}")
                continue

            # Get operator and value
            operator = filter_config.get("operator", "eq")
            value = filter_config.get("value")
            field = getattr(model_class, field_name)

            try:
                # Apply filter based on operator
                if operator == "eq":
                    query = query.filter(field == value)
                elif operator == "ne":
                    query = query.filter(field != value)
                elif operator == "in":
                    if not isinstance(value, list):
                        logger.warning(f"Operator 'in' requires a list, got {type(value)}")
                        continue
                    query = query.filter(field.in_(value))
                elif operator == "not_in":
                    if not isinstance(value, list):
                        logger.warning(f"Operator 'not_in' requires a list, got {type(value)}")
                        continue
                    query = query.filter(~field.in_(value))
                elif operator == "gt":
                    query = query.filter(field > value)
                elif operator == "gte":
                    query = query.filter(field >= value)
                elif operator == "lt":
                    query = query.filter(field < value)
                elif operator == "lte":
                    query = query.filter(field <= value)
                elif operator == "between":
                    if not isinstance(value, dict) or "min" not in value or "max" not in value:
                        logger.warning(
                            f"Operator 'between' requires {{'min': ..., 'max': ...}}, got {value}"
                        )
                        continue
                    query = query.filter(field.between(value["min"], value["max"]))
                elif operator == "contains":
                    query = query.filter(field.ilike(f"%{value}%"))
                elif operator == "starts_with":
                    query = query.filter(field.ilike(f"{value}%"))
                elif operator == "ends_with":
                    query = query.filter(field.ilike(f"%{value}"))
                elif operator == "is_null":
                    query = query.filter(field.is_(None))
                elif operator == "is_not_null":
                    query = query.filter(field.isnot(None))
                else:
                    logger.warning(f"Unknown operator '{operator}' for field '{field_name}'")
                    continue
            except Exception as e:
                logger.error(
                    f"Error applying filter '{field_name}' with operator '{operator}': {e}",
                    exc_info=True,
                )
                # Continue with other filters instead of failing completely
                continue

        return query




