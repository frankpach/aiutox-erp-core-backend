"""Integration tests for AutomationEngine."""

import pytest
from uuid import uuid4

from app.core.automation.engine import AutomationEngine
from app.core.pubsub.models import Event, EventMetadata
from app.models.automation import AutomationExecutionStatus, Rule
from app.repositories.automation_repository import AutomationRepository


@pytest.fixture
def automation_engine(db_session):
    """Create AutomationEngine instance."""
    return AutomationEngine(db_session)


@pytest.fixture
def test_rule(db_session, test_tenant):
    """Create a test rule."""
    repository = AutomationRepository(db_session)
    rule = repository.create_rule(
        {
            "tenant_id": test_tenant.id,
            "name": "Test Rule",
            "description": "Test rule for automation",
            "enabled": True,
            "trigger": {"type": "event", "event_type": "product.created"},
            "conditions": [
                {
                    "field": "metadata.additional_data.stock.quantity",
                    "operator": "<",
                    "value": 10,
                }
            ],
            "actions": [
                {
                    "type": "notification",
                    "template": "low_stock_alert",
                    "recipients": ["admin@tenant.com"],
                }
            ],
        }
    )
    return rule


@pytest.mark.asyncio
async def test_execute_rule_success(automation_engine, test_rule, test_tenant):
    """Test executing a rule successfully."""
    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=test_tenant.id,
        user_id=uuid4(),
        metadata=EventMetadata(
            source="test",
            version="1.0",
            additional_data={"stock": {"quantity": 5}},
        ),
    )

    execution = await automation_engine.execute_rule(test_rule, event)

    assert execution is not None
    assert execution.rule_id == test_rule.id
    assert execution.event_id == event.event_id
    assert execution.status == AutomationExecutionStatus.SUCCESS
    assert execution.result is not None


@pytest.mark.asyncio
async def test_execute_rule_conditions_not_met(automation_engine, test_rule, test_tenant):
    """Test executing a rule where conditions are not met."""
    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=test_tenant.id,
        user_id=uuid4(),
        metadata=EventMetadata(
            source="test",
            version="1.0",
            additional_data={"stock": {"quantity": 20}},  # Condition not met
        ),
    )

    execution = await automation_engine.execute_rule(test_rule, event)

    assert execution is not None
    assert execution.status == AutomationExecutionStatus.SKIPPED
    assert execution.result is not None
    assert execution.result.get("reason") == "conditions_not_met"


@pytest.mark.asyncio
async def test_execute_rule_disabled(automation_engine, db_session, test_tenant):
    """Test executing a disabled rule."""
    repository = AutomationRepository(db_session)
    disabled_rule = repository.create_rule(
        {
            "tenant_id": test_tenant.id,
            "name": "Disabled Rule",
            "enabled": False,
            "trigger": {"type": "event", "event_type": "product.created"},
            "actions": [{"type": "notification", "template": "test"}],
        }
    )

    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=test_tenant.id,
        user_id=uuid4(),
        metadata=EventMetadata(source="test", version="1.0"),
    )

    execution = await automation_engine.execute_rule(disabled_rule, event)

    assert execution.status == AutomationExecutionStatus.SKIPPED
    assert execution.result.get("reason") == "rule_disabled"


@pytest.mark.asyncio
async def test_execute_rule_idempotency(automation_engine, test_rule, test_tenant):
    """Test that same event is not processed twice (idempotency)."""
    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=test_tenant.id,
        user_id=uuid4(),
        metadata=EventMetadata(
            source="test",
            version="1.0",
            additional_data={"stock": {"quantity": 5}},
        ),
    )

    # First execution
    execution1 = await automation_engine.execute_rule(test_rule, event)
    assert execution1.status == AutomationExecutionStatus.SUCCESS

    # Second execution with same event_id
    execution2 = await automation_engine.execute_rule(test_rule, event)
    assert execution2.id == execution1.id  # Should return the same execution


@pytest.mark.asyncio
async def test_process_event(automation_engine, db_session, test_tenant):
    """Test processing an event with multiple matching rules."""
    repository = AutomationRepository(db_session)

    # Create multiple rules for the same event type
    rule1 = repository.create_rule(
        {
            "tenant_id": test_tenant.id,
            "name": "Rule 1",
            "enabled": True,
            "trigger": {"type": "event", "event_type": "product.created"},
            "actions": [{"type": "notification", "template": "test1"}],
        }
    )

    rule2 = repository.create_rule(
        {
            "tenant_id": test_tenant.id,
            "name": "Rule 2",
            "enabled": True,
            "trigger": {"type": "event", "event_type": "product.created"},
            "actions": [{"type": "notification", "template": "test2"}],
        }
    )

    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=test_tenant.id,
        user_id=uuid4(),
        metadata=EventMetadata(source="test", version="1.0"),
    )

    executions = await automation_engine.process_event(event)

    # Should execute both rules
    assert len(executions) == 2
    assert all(ex.status == AutomationExecutionStatus.SUCCESS for ex in executions)



