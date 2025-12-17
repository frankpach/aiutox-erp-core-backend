"""Unit tests for FilterParser."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Query, declarative_base

from app.core.filters import FilterParser

Base = declarative_base()


class FilterTestModel(Base):
    """Test model for filter testing."""

    __tablename__ = "filter_test_model"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    status = Column(String(50))
    price = Column(Integer)
    category_id = Column(Integer)


@pytest.fixture
def mock_query():
    """Create a mock SQLAlchemy query."""
    query = MagicMock(spec=Query)
    query.filter = MagicMock(return_value=query)
    return query


def test_filter_eq(mock_query):
    """Test eq operator."""
    filters = {"status": {"operator": "eq", "value": "active"}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_ne(mock_query):
    """Test ne operator."""
    filters = {"status": {"operator": "ne", "value": "deleted"}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_in(mock_query):
    """Test in operator."""
    filters = {"status": {"operator": "in", "value": ["active", "pending"]}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_not_in(mock_query):
    """Test not_in operator."""
    filters = {"status": {"operator": "not_in", "value": ["deleted", "archived"]}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_gt(mock_query):
    """Test gt operator."""
    filters = {"price": {"operator": "gt", "value": 100}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_gte(mock_query):
    """Test gte operator."""
    filters = {"price": {"operator": "gte", "value": 100}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_lt(mock_query):
    """Test lt operator."""
    filters = {"price": {"operator": "lt", "value": 1000}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_lte(mock_query):
    """Test lte operator."""
    filters = {"price": {"operator": "lte", "value": 1000}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_between(mock_query):
    """Test between operator."""
    filters = {"price": {"operator": "between", "value": {"min": 100, "max": 500}}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_contains(mock_query):
    """Test contains operator."""
    filters = {"name": {"operator": "contains", "value": "laptop"}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_starts_with(mock_query):
    """Test starts_with operator."""
    filters = {"name": {"operator": "starts_with", "value": "Pro"}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_ends_with(mock_query):
    """Test ends_with operator."""
    filters = {"name": {"operator": "ends_with", "value": "2024"}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_is_null(mock_query):
    """Test is_null operator."""
    filters = {"category_id": {"operator": "is_null", "value": None}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_is_not_null(mock_query):
    """Test is_not_null operator."""
    filters = {"category_id": {"operator": "is_not_null", "value": None}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()


def test_filter_unknown_field(mock_query):
    """Test that unknown fields are ignored."""
    filters = {"unknown_field": {"operator": "eq", "value": "test"}}
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    # Should not call filter for unknown field
    mock_query.filter.assert_not_called()


def test_filter_multiple_filters(mock_query):
    """Test applying multiple filters."""
    filters = {
        "status": {"operator": "eq", "value": "active"},
        "price": {"operator": "gte", "value": 100},
        "name": {"operator": "contains", "value": "laptop"},
    }
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    # Should call filter 3 times
    assert mock_query.filter.call_count == 3


def test_filter_default_operator(mock_query):
    """Test that default operator is eq when not specified."""
    filters = {"status": {"value": "active"}}  # No operator specified
    result = FilterParser.apply_filters(mock_query, FilterTestModel, filters)

    assert result == mock_query
    mock_query.filter.assert_called_once()



