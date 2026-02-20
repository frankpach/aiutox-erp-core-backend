"""Integration tests for CRM module."""

from fastapi import status

from app.models.module_role import ModuleRole
from app.services.auth_service import AuthService


class TestCRM:
    def test_list_pipelines_requires_permission(
        self, client_with_db, db_session, test_user
    ):
        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        response = client_with_db.get(
            "/api/v1/crm/pipelines",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_and_list_pipeline_with_permission(
        self, client_with_db, db_session, test_user
    ):
        db_session.add(
            ModuleRole(
                user_id=test_user.id,
                module="crm",
                role_name="editor",
                granted_by=test_user.id,
            )
        )
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        create_resp = client_with_db.post(
            "/api/v1/crm/pipelines",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "Default",
                "description": "Main pipeline",
                "is_default": True,
            },
        )
        assert create_resp.status_code == status.HTTP_201_CREATED

        list_resp = client_with_db.get(
            "/api/v1/crm/pipelines",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert list_resp.status_code == status.HTTP_200_OK
        payload = list_resp.json()
        assert isinstance(payload.get("data"), list)

    def test_create_lead_with_permission(self, client_with_db, db_session, test_user):
        db_session.add(
            ModuleRole(
                user_id=test_user.id,
                module="crm",
                role_name="editor",
                granted_by=test_user.id,
            )
        )
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        resp = client_with_db.post(
            "/api/v1/crm/leads",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"title": "Inbound Lead", "status": "new"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()["data"]
        assert data["title"] == "Inbound Lead"

    def test_create_opportunity_with_permission(
        self, client_with_db, db_session, test_user
    ):
        db_session.add(
            ModuleRole(
                user_id=test_user.id,
                module="crm",
                role_name="editor",
                granted_by=test_user.id,
            )
        )
        db_session.commit()

        auth_service = AuthService(db_session)
        access_token = auth_service.create_access_token_for_user(test_user)

        resp = client_with_db.post(
            "/api/v1/crm/opportunities",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Deal 1", "status": "open"},
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()["data"]
        assert data["name"] == "Deal 1"
