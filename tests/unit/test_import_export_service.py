"""Unit tests for ImportExportService."""

import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from app.core.import_export.service import DataExporter, DataImporter, ImportExportService
from app.core.pubsub import EventPublisher


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = MagicMock()
    return publisher


@pytest.fixture
def data_exporter(db_session):
    """Create DataExporter instance."""
    return DataExporter(db_session)


@pytest.fixture
def data_importer(db_session):
    """Create DataImporter instance."""
    return DataImporter(db_session)


@pytest.fixture
def import_export_service(db_session, mock_event_publisher):
    """Create ImportExportService instance."""
    return ImportExportService(db=db_session, event_publisher=mock_event_publisher)


def test_export_to_csv(data_exporter):
    """Test exporting data to CSV."""
    data = [
        {"name": "Product 1", "price": "10.00"},
        {"name": "Product 2", "price": "20.00"},
    ]

    csv_data = data_exporter.export_to_csv(data, columns=["name", "price"])

    assert csv_data is not None
    assert b"name" in csv_data
    assert b"Product 1" in csv_data
    assert b"Product 2" in csv_data


def test_import_from_csv(data_importer):
    """Test importing data from CSV."""
    csv_content = b"name,price\nProduct 1,10.00\nProduct 2,20.00"

    data = data_importer.import_from_csv(csv_content, delimiter=",", skip_header=True)

    assert len(data) == 2
    assert data[0]["name"] == "Product 1"
    assert data[0]["price"] == "10.00"
    assert data[1]["name"] == "Product 2"
    assert data[1]["price"] == "20.00"


def test_validate_data(data_importer):
    """Test validating imported data."""
    data = [
        {"name": "Product 1", "price": "10"},
        {"name": "", "price": "20"},  # Missing name
    ]

    validation_rules = {
        "name": {"required": True},
        "price": {"type": "int"},
    }

    valid_rows, invalid_rows = data_importer.validate_data(data, validation_rules)

    assert len(valid_rows) == 1
    assert len(invalid_rows) == 1
    assert invalid_rows[0]["errors"][0] == "name is required"


def test_create_import_job(import_export_service, test_user, test_tenant, mock_event_publisher):
    """Test creating an import job."""
    job = import_export_service.create_import_job(
        job_data={
            "module": "products",
            "file_name": "products.csv",
            "status": "pending",
        },
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )

    assert job.module == "products"
    assert job.file_name == "products.csv"
    assert job.tenant_id == test_tenant.id
    assert job.created_by == test_user.id

    # Verify event was published
    assert mock_event_publisher.publish.called








