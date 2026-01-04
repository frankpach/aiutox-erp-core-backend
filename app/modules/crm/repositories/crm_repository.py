from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.crm.models.crm import Lead, Opportunity, Pipeline


class CRMRepository:
    def __init__(self, db: Session):
        self.db = db

    # Pipelines
    def create_pipeline(self, data: dict) -> Pipeline:
        pipeline = Pipeline(**data)
        self.db.add(pipeline)
        self.db.commit()
        self.db.refresh(pipeline)
        return pipeline

    def list_pipelines(self, tenant_id: UUID, skip: int = 0, limit: int = 100) -> list[Pipeline]:
        return (
            self.db.query(Pipeline)
            .filter(Pipeline.tenant_id == tenant_id)
            .order_by(Pipeline.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_pipeline(self, pipeline_id: UUID, tenant_id: UUID) -> Pipeline | None:
        return (
            self.db.query(Pipeline)
            .filter(Pipeline.id == pipeline_id, Pipeline.tenant_id == tenant_id)
            .first()
        )

    def update_pipeline(self, pipeline: Pipeline, data: dict) -> Pipeline:
        for key, value in data.items():
            setattr(pipeline, key, value)
        self.db.commit()
        self.db.refresh(pipeline)
        return pipeline

    def delete_pipeline(self, pipeline: Pipeline) -> None:
        self.db.delete(pipeline)
        self.db.commit()

    # Leads
    def create_lead(self, data: dict) -> Lead:
        lead = Lead(**data)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def list_leads(
        self,
        tenant_id: UUID,
        status: str | None = None,
        pipeline_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Lead]:
        query = self.db.query(Lead).filter(Lead.tenant_id == tenant_id)
        if status:
            query = query.filter(Lead.status == status)
        if pipeline_id:
            query = query.filter(Lead.pipeline_id == pipeline_id)
        return query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()

    def get_lead(self, lead_id: UUID, tenant_id: UUID) -> Lead | None:
        return (
            self.db.query(Lead)
            .filter(Lead.id == lead_id, Lead.tenant_id == tenant_id)
            .first()
        )

    def update_lead(self, lead: Lead, data: dict) -> Lead:
        for key, value in data.items():
            setattr(lead, key, value)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def delete_lead(self, lead: Lead) -> None:
        self.db.delete(lead)
        self.db.commit()

    # Opportunities
    def create_opportunity(self, data: dict) -> Opportunity:
        opp = Opportunity(**data)
        self.db.add(opp)
        self.db.commit()
        self.db.refresh(opp)
        return opp

    def list_opportunities(
        self,
        tenant_id: UUID,
        status: str | None = None,
        pipeline_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Opportunity]:
        query = self.db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id)
        if status:
            query = query.filter(Opportunity.status == status)
        if pipeline_id:
            query = query.filter(Opportunity.pipeline_id == pipeline_id)
        return query.order_by(Opportunity.created_at.desc()).offset(skip).limit(limit).all()

    def get_opportunity(self, opportunity_id: UUID, tenant_id: UUID) -> Opportunity | None:
        return (
            self.db.query(Opportunity)
            .filter(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id)
            .first()
        )

    def update_opportunity(self, opportunity: Opportunity, data: dict) -> Opportunity:
        for key, value in data.items():
            setattr(opportunity, key, value)
        self.db.commit()
        self.db.refresh(opportunity)
        return opportunity

    def delete_opportunity(self, opportunity: Opportunity) -> None:
        self.db.delete(opportunity)
        self.db.commit()
