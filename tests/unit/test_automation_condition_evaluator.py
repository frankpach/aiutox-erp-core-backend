"""Unit tests for ConditionEvaluator."""

from uuid import uuid4

import pytest

from app.core.automation.condition_evaluator import ConditionEvaluator
from app.core.pubsub.models import Event, EventMetadata


@pytest.fixture
def condition_evaluator():
    """Create ConditionEvaluator instance."""
    return ConditionEvaluator()


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        metadata=EventMetadata(
            source="test",
            version="1.0",
            additional_data={"stock": {"quantity": 5}, "price": 100.50},
        ),
    )


@pytest.mark.asyncio
async def test_evaluate_empty_conditions(condition_evaluator, sample_event):
    """Test that empty conditions return True."""
    result = condition_evaluator.evaluate([], sample_event)
    assert result is True


@pytest.mark.asyncio
async def test_evaluate_equals_condition(condition_evaluator, sample_event):
    """Test equals operator."""
    conditions = [{"field": "event_type", "operator": "==", "value": "product.created"}]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is True

    conditions = [{"field": "event_type", "operator": "==", "value": "product.updated"}]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_not_equals_condition(condition_evaluator, sample_event):
    """Test not equals operator."""
    conditions = [{"field": "event_type", "operator": "!=", "value": "product.updated"}]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is True


@pytest.mark.asyncio
async def test_evaluate_greater_than_condition(condition_evaluator, sample_event):
    """Test greater than operator."""
    conditions = [
        {"field": "metadata.additional_data.price", "operator": ">", "value": 50}
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is True

    conditions = [
        {"field": "metadata.additional_data.price", "operator": ">", "value": 200}
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_less_than_condition(condition_evaluator, sample_event):
    """Test less than operator."""
    conditions = [
        {
            "field": "metadata.additional_data.stock.quantity",
            "operator": "<",
            "value": 10,
        }
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is True

    conditions = [
        {
            "field": "metadata.additional_data.stock.quantity",
            "operator": "<",
            "value": 3,
        }
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_in_condition(condition_evaluator, sample_event):
    """Test in operator."""
    conditions = [
        {
            "field": "event_type",
            "operator": "in",
            "value": ["product.created", "product.updated"],
        }
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is True

    conditions = [
        {
            "field": "event_type",
            "operator": "in",
            "value": ["product.deleted", "product.updated"],
        }
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_contains_condition(condition_evaluator, sample_event):
    """Test contains operator."""
    conditions = [{"field": "event_type", "operator": "contains", "value": "product"}]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is True

    conditions = [{"field": "event_type", "operator": "contains", "value": "inventory"}]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_multiple_conditions_all_met(condition_evaluator, sample_event):
    """Test multiple conditions where all are met."""
    conditions = [
        {"field": "event_type", "operator": "==", "value": "product.created"},
        {
            "field": "metadata.additional_data.stock.quantity",
            "operator": "<",
            "value": 10,
        },
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is True


@pytest.mark.asyncio
async def test_evaluate_multiple_conditions_one_not_met(
    condition_evaluator, sample_event
):
    """Test multiple conditions where one is not met."""
    conditions = [
        {"field": "event_type", "operator": "==", "value": "product.created"},
        {
            "field": "metadata.additional_data.stock.quantity",
            "operator": "<",
            "value": 3,
        },
    ]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_invalid_field_path(condition_evaluator, sample_event):
    """Test that invalid field path returns False."""
    conditions = [{"field": "nonexistent.field", "operator": "==", "value": "test"}]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False


@pytest.mark.asyncio
async def test_evaluate_unknown_operator(condition_evaluator, sample_event):
    """Test that unknown operator returns False."""
    conditions = [{"field": "event_type", "operator": "unknown", "value": "test"}]
    result = condition_evaluator.evaluate(conditions, sample_event)
    assert result is False
