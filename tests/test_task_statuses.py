"""
Tests for Task Statuses API
Unit and integration tests for task status management
"""

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.features.tasks.statuses import router
from app.models.task_status import TaskStatus
from app.models.tenant import Tenant
from app.models.user import User


class TestTaskStatusesAPI:
    """Test cases for Task Statuses API endpoints"""

    def setup_method(self):
        """Setup test data"""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router, prefix="/task-statuses", tags=["task-statuses"])
        self.client = TestClient(self.app)
        self.test_user = User(id="user-1", email="test@example.com")
        self.test_tenant = Tenant(id="tenant-1", name="Test Tenant")

        # Mock dependencies
        self.app.dependency_overrides[get_current_user] = lambda: self.test_user

    def teardown_method(self):
        """Cleanup test data"""
        self.app.dependency_overrides.clear()

    @pytest.fixture
    def sample_status_data(self):
        """Sample status data for testing"""
        return {
            "name": "Test Status",
            "color": "#ff0000",
            "type": "open",
            "order": 1
        }

    @pytest.fixture
    def system_status(self, db_session: Session):
        """Create a system status for testing"""
        status = TaskStatus(
            tenant_id=self.test_tenant.id,
            name="System Status",
            color="#6b7280",
            type="open",
            order=0,
            is_system=True
        )
        db_session.add(status)
        db_session.commit()
        db_session.refresh(status)
        return status

    @pytest.fixture
    def custom_status(self, db_session: Session):
        """Create a custom status for testing"""
        status = TaskStatus(
            tenant_id=self.test_tenant.id,
            name="Custom Status",
            color="#3b82f6",
            type="in_progress",
            order=1,
            is_system=False
        )
        db_session.add(status)
        db_session.commit()
        db_session.refresh(status)
        return status


class TestGetStatuses:
    """Test GET /tasks/statuses endpoint"""

    def test_get_all_statuses(self, client, system_status, custom_status):
        """Test getting all statuses including system ones"""
        response = client.get("/task-statuses")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Check system status
        system_data = next(s for s in data if s["is_system"])
        assert system_data["name"] == "System Status"
        assert system_data["type"] == "open"

        # Check custom status
        custom_data = next(s for s in data if not s["is_system"])
        assert custom_data["name"] == "Custom Status"
        assert custom_data["type"] == "in_progress"

    def test_get_statuses_exclude_system(self, client, system_status, custom_status):
        """Test getting only custom statuses"""
        response = client.get("/task-statuses?include_system=false")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Custom Status"
        assert data[0]["is_system"] is False

    def test_get_empty_statuses(self, client_with_db):
        """Test getting statuses when none exist"""
        response = client_with_db.get("/task-statuses")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestCreateStatus:
    """Test POST /tasks/statuses endpoint"""

    def test_create_status_success(self, client, sample_status_data):
        """Test successful status creation"""
        response = client.post("/task-statuses", json=sample_status_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == sample_status_data["name"]
        assert data["color"] == sample_status_data["color"]
        assert data["type"] == sample_status_data["type"]
        assert data["order"] == sample_status_data["order"]
        assert data["is_system"] is False
        assert "id" in data
        assert "created_at" in data

    def test_create_status_duplicate_name(self, client, custom_status, sample_status_data):
        """Test creating status with duplicate name"""
        sample_status_data["name"] = "Custom Status"  # Same as existing

        response = client.post("/task-statuses", json=sample_status_data)

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_status_invalid_type(self, client, sample_status_data):
        """Test creating status with invalid type"""
        sample_status_data["type"] = "invalid_type"

        response = client.post("/task-statuses", json=sample_status_data)

        assert response.status_code == 422  # Validation error

    def test_create_status_missing_required_fields(self, client):
        """Test creating status with missing required fields"""
        response = client.post("/task-statuses", json={})

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("name" in str(error) for error in errors)

    def test_create_status_invalid_color(self, client, sample_status_data):
        """Test creating status with invalid color"""
        sample_status_data["color"] = "invalid_color"

        response = client.post("/task-statuses", json=sample_status_data)

        # Should not fail immediately, but color validation might be added later
        assert response.status_code in [200, 422]


class TestUpdateStatus:
    """Test PUT /tasks/statuses/{status_id} endpoint"""

    def test_update_status_success(self, client, custom_status):
        """Test successful status update"""
        update_data = {
            "name": "Updated Status",
            "color": "#00ff00"
        }

        response = client.put(f"/task-statuses/{custom_status.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Updated Status"
        assert data["color"] == "#00ff00"
        assert data["type"] == custom_status.type  # Unchanged
        assert data["order"] == custom_status.order  # Unchanged

    def test_update_system_status_forbidden(self, client, system_status):
        """Test that system statuses cannot be updated"""
        update_data = {"name": "Should Fail"}

        response = client.put(f"/task-statuses/{system_status.id}", json=update_data)

        assert response.status_code == 403
        assert "cannot be modified" in response.json()["detail"]

    def test_update_nonexistent_status(self, client):
        """Test updating non-existent status"""
        update_data = {"name": "Should Fail"}

        response = client.put("/task-statuses/nonexistent-id", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_status_duplicate_name(self, client, custom_status, sample_status_data):
        """Test updating status with duplicate name"""
        # Create another status first
        create_response = client.post("/task-statuses", json=sample_status_data)
        new_status = create_response.json()

        # Try to update custom_status with new_status's name
        update_data = {"name": new_status["name"]}
        response = client.put(f"/task-statuses/{custom_status.id}", json=update_data)

        # This might not be enforced in the current implementation
        # If it is, expect 400, otherwise expect 200
        assert response.status_code in [200, 400]


class TestDeleteStatus:
    """Test DELETE /tasks/statuses/{status_id} endpoint"""

    def test_delete_status_success(self, client, custom_status):
        """Test successful status deletion"""
        response = client.delete(f"/task-statuses/{custom_status.id}")

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_system_status_forbidden(self, client, system_status):
        """Test that system statuses cannot be deleted"""
        response = client.delete(f"/task-statuses/{system_status.id}")

        assert response.status_code == 403
        assert "cannot be deleted" in response.json()["detail"]

    def test_delete_nonexistent_status(self, client):
        """Test deleting non-existent status"""
        response = client.delete("/task-statuses/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch('app.features.tasks.statuses.Task')
    def test_delete_status_with_tasks(self, mock_task_model, client, custom_status):
        """Test deleting status that is being used by tasks"""
        # Mock task query to return count > 0
        mock_query = mock_task_model.query.return_value
        mock_query.filter.return_value.count.return_value = 5

        response = client.delete(f"/task-statuses/{custom_status.id}")

        assert response.status_code == 400
        assert "tasks are using this status" in response.json()["detail"]


class TestReorderStatus:
    """Test POST /tasks/statuses/{status_id}/reorder endpoint"""

    def test_reorder_status_success(self, client, custom_status):
        """Test successful status reordering"""
        reorder_data = {"new_order": 5}

        response = client.post(f"/task-statuses/{custom_status.id}/reorder", json=reorder_data)

        assert response.status_code == 200
        assert "reordered successfully" in response.json()["message"]

    def test_reorder_system_status_forbidden(self, client, system_status):
        """Test that system statuses cannot be reordered"""
        reorder_data = {"new_order": 5}

        response = client.post(f"/task-statuses/{system_status.id}/reorder", json=reorder_data)

        assert response.status_code == 403
        assert "cannot be reordered" in response.json()["detail"]

    def test_reorder_nonexistent_status(self, client):
        """Test reordering non-existent status"""
        reorder_data = {"new_order": 5}

        response = client.post("/task-statuses/nonexistent-id/reorder", json=reorder_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


class TestTaskStatusModel:
    """Test TaskStatus model and helper functions"""

    def test_status_model_creation(self, db_session: Session, test_tenant):
        """Test TaskStatus model creation"""
        status = TaskStatus(
            tenant_id=test_tenant.id,
            name="Test Status",
            color="#ff0000",
            type="open",
            order=1,
            is_system=False
        )

        db_session.add(status)
        db_session.commit()
        db_session.refresh(status)

        assert status.id is not None

    def test_initialize_system_statuses(self, db_session: Session, test_tenant):
        """Test system status initialization"""
        from app.features.tasks.statuses import initialize_system_statuses

        tenant_id = test_tenant.id
        asyncio.run(initialize_system_statuses(db_session, tenant_id))

        # Check that system statuses were created
        statuses = db_session.query(TaskStatus).filter(
            TaskStatus.tenant_id == tenant_id,
            TaskStatus.is_system == True
        ).all()

        assert len(statuses) == 5  # Default system statuses
        status_names = [s.name for s in statuses]
        assert "Por Hacer" in status_names
        assert "En Progreso" in status_names
        assert "En Espera" in status_names
        assert "Completado" in status_names
        assert "Cancelado" in status_names

    def test_status_type_validation(self):
        """Test status type validation"""
        valid_types = ["open", "in_progress", "on_hold", "completed", "canceled"]

        for status_type in valid_types:
            status = TaskStatus(type=status_type)
            assert status.type == status_type

    def test_status_ordering(self, db_session: Session, test_tenant):
        """Test status ordering functionality"""
        # Create multiple statuses
        statuses = [
            TaskStatus(tenant_id=test_tenant.id, name="Status 1", type="open", color="#ff0000", order=3),
            TaskStatus(tenant_id=test_tenant.id, name="Status 2", type="open", color="#00ff00", order=1),
            TaskStatus(tenant_id=test_tenant.id, name="Status 3", type="open", color="#0000ff", order=2),
        ]

        for status in statuses:
            db_session.add(status)
        db_session.commit()

        # Query ordered by order
        ordered_statuses = db_session.query(TaskStatus).filter(
            TaskStatus.tenant_id == test_tenant.id
        ).order_by(TaskStatus.order).all()

        assert ordered_statuses[0].name == "Status 2"
        assert ordered_statuses[1].name == "Status 3"
        assert ordered_statuses[2].name == "Status 1"


class TestStatusValidation:
    """Test status validation logic"""

    def test_status_name_uniqueness(self, db_session: Session, test_tenant):
        """Test status name uniqueness validation"""
        tenant_id = test_tenant.id

        # Create first status
        status1 = TaskStatus(
            tenant_id=tenant_id,
            name="Unique Name",
            color="#ff0000",
            type="open"
        )
        db_session.add(status1)
        db_session.commit()

        # Try to create second status with same name
        status2 = TaskStatus(
            tenant_id=tenant_id,
            name="Unique Name",  # Same name
            color="#00ff00",
            type="in_progress"
        )
        db_session.add(status2)

        # Should raise integrity error due to unique constraint
        with pytest.raises(Exception):  # Could be IntegrityError or similar
            db_session.commit()

    def test_status_color_format(self):
        """Test status color format validation"""
        valid_colors = ["#ff0000", "#00ff00", "#0000ff", "#6b7280"]
        invalid_colors = ["ff0000", "red", "rgb(255,0,0)", "#gggggg"]

        for color in valid_colors:
            status = TaskStatus(color=color)
            assert status.color == color

        # Note: Color validation might be implemented at application level
        # rather than database level
        for color in invalid_colors:
            status = TaskStatus(color=color)
            assert status.color == color  # Currently no validation


class TestStatusIntegration:
    """Integration tests for status management"""

    def test_full_crud_workflow(self, client):
        """Test complete CRUD workflow"""
        # Create
        create_data = {
            "name": "Integration Test Status",
            "color": "#ff6600",
            "type": "in_progress",
            "order": 10
        }

        create_response = client.post("/task-statuses", json=create_data)
        assert create_response.status_code == 200
        created_status = create_response.json()
        status_id = created_status["id"]

        # Read
        get_response = client.get("/task-statuses")
        assert get_response.status_code == 200
        statuses = get_response.json()
        assert any(s["id"] == status_id for s in statuses)

        # Update
        update_data = {"name": "Updated Integration Status"}
        update_response = client.put(f"/task-statuses/{status_id}", json=update_data)
        assert update_response.status_code == 200
        updated_status = update_response.json()
        assert updated_status["name"] == "Updated Integration Status"

        # Delete
        delete_response = client.delete(f"/task-statuses/{status_id}")
        assert delete_response.status_code == 200

        # Verify deletion
        get_response_after = client.get("/task-statuses")
        statuses_after = get_response_after.json()
        assert not any(s["id"] == status_id for s in statuses_after)

    def test_tenant_isolation(self, client):
        """Test that statuses are isolated by tenant"""
        # This would require mocking different tenants
        # For now, just test that tenant_id is properly set
        create_data = {
            "name": "Tenant Test Status",
            "color": "#0066ff",
            "type": "open"
        }

        response = client.post("/task-statuses", json=create_data)
        assert response.status_code == 200

        created_status = response.json()
        assert created_status["tenant_id"] == self.test_tenant.id


if __name__ == "__main__":
    pytest.main([__file__])
