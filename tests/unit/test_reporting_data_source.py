"""Unit tests for BaseDataSource and ProductsDataSource."""


import pytest

from app.core.reporting.data_source import BaseDataSource
from app.core.reporting.sources.products_data_source import ProductsDataSource


def test_base_data_source_is_abstract(db_session, test_tenant):
    """Test that BaseDataSource cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseDataSource(db_session, test_tenant.id)


@pytest.mark.asyncio
async def test_products_data_source_get_columns(db_session, test_tenant):
    """Test ProductsDataSource get_columns."""
    data_source = ProductsDataSource(db_session, test_tenant.id)
    columns = data_source.get_columns()

    assert len(columns) > 0
    assert all("name" in col and "type" in col and "label" in col for col in columns)


@pytest.mark.asyncio
async def test_products_data_source_get_filters(db_session, test_tenant):
    """Test ProductsDataSource get_filters."""
    data_source = ProductsDataSource(db_session, test_tenant.id)
    filters = data_source.get_filters()

    assert len(filters) > 0
    assert all("name" in f and "type" in f and "label" in f for f in filters)










