"""Unit tests for RuleParser."""

import pytest

from app.core.automation.rule_parser import RuleParser


@pytest.fixture
def rule_parser():
    """Create RuleParser instance."""
    return RuleParser()


@pytest.fixture
def valid_rule_definition():
    """Create a valid rule definition."""
    return {
        "name": "Test Rule",
        "description": "Test description",
        "enabled": True,
        "trigger": {"type": "event", "event_type": "product.created"},
        "conditions": [
            {"field": "metadata.stock.quantity", "operator": "<", "value": 10}
        ],
        "actions": [
            {
                "type": "notification",
                "template": "low_stock_alert",
                "recipients": ["admin@tenant.com"],
            }
        ],
    }


def test_parse_valid_rule(rule_parser, valid_rule_definition):
    """Test parsing a valid rule definition."""
    result = rule_parser.parse(valid_rule_definition)
    assert result["name"] == "Test Rule"
    assert result["enabled"] is True
    assert result["trigger"]["type"] == "event"
    assert len(result["actions"]) == 1


def test_parse_rule_missing_name(rule_parser):
    """Test parsing rule without name."""
    rule_def = {
        "trigger": {"type": "event", "event_type": "product.created"},
        "actions": [{"type": "notification", "template": "test"}],
    }
    with pytest.raises(ValueError, match="Missing required field: name"):
        rule_parser.parse(rule_def)


def test_parse_rule_missing_trigger(rule_parser):
    """Test parsing rule without trigger."""
    rule_def = {
        "name": "Test Rule",
        "actions": [{"type": "notification", "template": "test"}],
    }
    with pytest.raises(ValueError, match="Missing required field: trigger"):
        rule_parser.parse(rule_def)


def test_parse_rule_missing_actions(rule_parser):
    """Test parsing rule without actions."""
    rule_def = {
        "name": "Test Rule",
        "trigger": {"type": "event", "event_type": "product.created"},
    }
    with pytest.raises(ValueError, match="Missing required field: actions"):
        rule_parser.parse(rule_def)


def test_parse_rule_invalid_trigger_type(rule_parser):
    """Test parsing rule with invalid trigger type."""
    rule_def = {
        "name": "Test Rule",
        "trigger": {"type": "invalid"},
        "actions": [{"type": "notification", "template": "test"}],
    }
    with pytest.raises(ValueError, match="Unknown trigger type"):
        rule_parser.parse(rule_def)


def test_parse_rule_event_trigger_missing_event_type(rule_parser):
    """Test parsing rule with event trigger missing event_type."""
    rule_def = {
        "name": "Test Rule",
        "trigger": {"type": "event"},
        "actions": [{"type": "notification", "template": "test"}],
    }
    with pytest.raises(ValueError, match="event trigger must have 'event_type' field"):
        rule_parser.parse(rule_def)


def test_parse_rule_empty_actions(rule_parser):
    """Test parsing rule with empty actions."""
    rule_def = {
        "name": "Test Rule",
        "trigger": {"type": "event", "event_type": "product.created"},
        "actions": [],
    }
    with pytest.raises(ValueError, match="actions must be a non-empty list"):
        rule_parser.parse(rule_def)


def test_parse_rule_action_missing_type(rule_parser):
    """Test parsing rule with action missing type."""
    rule_def = {
        "name": "Test Rule",
        "trigger": {"type": "event", "event_type": "product.created"},
        "actions": [{"template": "test"}],
    }
    with pytest.raises(ValueError, match="Each action must have a 'type' field"):
        rule_parser.parse(rule_def)


def test_parse_rule_without_conditions(rule_parser):
    """Test parsing rule without conditions."""
    rule_def = {
        "name": "Test Rule",
        "trigger": {"type": "event", "event_type": "product.created"},
        "actions": [{"type": "notification", "template": "test"}],
    }
    result = rule_parser.parse(rule_def)
    assert result["conditions"] == []


def test_validate_valid_rule(rule_parser, valid_rule_definition):
    """Test validating a valid rule."""
    assert rule_parser.validate(valid_rule_definition) is True


def test_validate_invalid_rule(rule_parser):
    """Test validating an invalid rule."""
    rule_def = {
        "name": "Test Rule",
        # Missing trigger and actions
    }
    assert rule_parser.validate(rule_def) is False


