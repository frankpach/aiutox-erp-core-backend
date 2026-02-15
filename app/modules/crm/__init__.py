from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface, ModuleNavigationItem
from app.modules.crm.api import router
from app.modules.crm.models.crm import Lead, Opportunity, Pipeline
from app.modules.crm.permissions import CRM_MANAGE, CRM_VIEW


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

    def get_navigation_items(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="crm.main",
                label="CRM",
                path="/crm",
                permission=CRM_VIEW,
                icon="grid",
                order=0,
            ),
            ModuleNavigationItem(
                id="crm.pipeline",
                label="Pipelines",
                path="/crm/pipelines",
                permission=CRM_VIEW,
                icon="grid",
                order=10,
            ),
        ]

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="crm.config",
                label="Configuración CRM",
                path="/config/modules?module=crm",
                permission=CRM_MANAGE,
                icon="settings",
                category="Configuración",
                order=0,
            )
        ]


def create_module(db: Session | None = None) -> CRMModule:
    return CRMModule(db)
