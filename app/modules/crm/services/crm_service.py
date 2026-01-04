from __future__ import annotations

from uuid import UUID

from app.core.exceptions import raise_not_found
from app.modules.crm.repositories.crm_repository import CRMRepository


class CRMService:
    def __init__(self, db):
        self.repository = CRMRepository(db)

    # Pipelines
    def create_pipeline(self, tenant_id: UUID, data: dict):
        return self.repository.create_pipeline({**data, "tenant_id": tenant_id})

    def list_pipelines(self, tenant_id: UUID, skip: int = 0, limit: int = 100):
        return self.repository.list_pipelines(tenant_id=tenant_id, skip=skip, limit=limit)

    def get_pipeline(self, tenant_id: UUID, pipeline_id: UUID):
        pipeline = self.repository.get_pipeline(pipeline_id=pipeline_id, tenant_id=tenant_id)
        if not pipeline:
            raise_not_found("Pipeline", str(pipeline_id))
        return pipeline

    def update_pipeline(self, tenant_id: UUID, pipeline_id: UUID, data: dict):
        pipeline = self.get_pipeline(tenant_id=tenant_id, pipeline_id=pipeline_id)
        return self.repository.update_pipeline(pipeline, data)

    def delete_pipeline(self, tenant_id: UUID, pipeline_id: UUID):
        pipeline = self.get_pipeline(tenant_id=tenant_id, pipeline_id=pipeline_id)
        self.repository.delete_pipeline(pipeline)

    # Leads
    def create_lead(self, tenant_id: UUID, user_id: UUID, data: dict):
        return self.repository.create_lead({**data, "tenant_id": tenant_id, "created_by_id": user_id})

    def list_leads(
        self,
        tenant_id: UUID,
        status: str | None = None,
        pipeline_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return self.repository.list_leads(
            tenant_id=tenant_id,
            status=status,
            pipeline_id=pipeline_id,
            skip=skip,
            limit=limit,
        )

    def get_lead(self, tenant_id: UUID, lead_id: UUID):
        lead = self.repository.get_lead(lead_id=lead_id, tenant_id=tenant_id)
        if not lead:
            raise_not_found("Lead", str(lead_id))
        return lead

    def update_lead(self, tenant_id: UUID, lead_id: UUID, data: dict):
        lead = self.get_lead(tenant_id=tenant_id, lead_id=lead_id)
        return self.repository.update_lead(lead, data)

    def delete_lead(self, tenant_id: UUID, lead_id: UUID):
        lead = self.get_lead(tenant_id=tenant_id, lead_id=lead_id)
        self.repository.delete_lead(lead)

    # Opportunities
    def create_opportunity(self, tenant_id: UUID, user_id: UUID, data: dict):
        return self.repository.create_opportunity({**data, "tenant_id": tenant_id, "created_by_id": user_id})

    def list_opportunities(
        self,
        tenant_id: UUID,
        status: str | None = None,
        pipeline_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return self.repository.list_opportunities(
            tenant_id=tenant_id,
            status=status,
            pipeline_id=pipeline_id,
            skip=skip,
            limit=limit,
        )

    def get_opportunity(self, tenant_id: UUID, opportunity_id: UUID):
        opp = self.repository.get_opportunity(opportunity_id=opportunity_id, tenant_id=tenant_id)
        if not opp:
            raise_not_found("Opportunity", str(opportunity_id))
        return opp

    def update_opportunity(self, tenant_id: UUID, opportunity_id: UUID, data: dict):
        opp = self.get_opportunity(tenant_id=tenant_id, opportunity_id=opportunity_id)
        return self.repository.update_opportunity(opp, data)

    def delete_opportunity(self, tenant_id: UUID, opportunity_id: UUID):
        opp = self.get_opportunity(tenant_id=tenant_id, opportunity_id=opportunity_id)
        self.repository.delete_opportunity(opp)
