from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface
from app.modules.crm.api import router
from app.modules.crm.models.crm import Lead, Opportunity, Pipeline


class CRMModule(ModuleInterface):
    def __init__(self, db: Session | None = None):
        self._db = db
        self._config_service = ConfigService(db) if db else None

    @property
    def module_id(self) -> str:
        return "crm"

    @property
    def module_type(self) -> str:
        return "business"

    @property
    def enabled(self) -> bool:
        if self._db and self._config_service:
            try:
                return True
            except Exception:
                pass
        return True

    def get_router(self) -> APIRouter | None:
        return router

    def get_models(self) -> list:
        return [Pipeline, Lead, Opportunity]

    def get_dependencies(self) -> list[str]:
        return ["auth", "users", "pubsub"]

    @property
    def module_name(self) -> str:
        return "CRM"

    @property
    def description(self) -> str:
        return "Módulo empresarial: leads, oportunidades y pipelines."


def create_module(db: Session | None = None) -> CRMModule:
    return CRMModule(db)
