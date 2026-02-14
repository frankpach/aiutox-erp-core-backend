"""Gamification module for AiutoX ERP.

Provides points, badges, leaderboards, and event-driven gamification.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.module_interface import ModuleInterface
from app.models.gamification import (
    Badge,
    GamificationEvent,
    LeaderboardEntry,
    UserBadge,
    UserPoints,
)


class GamificationModule(ModuleInterface):
    """Gamification module for points, badges, and leaderboards."""

    def __init__(self, db: Session | None = None):
        self._db = db
        self._config_service = ConfigService(db) if db else None

    @property
    def module_id(self) -> str:
        return "gamification"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_router(self) -> APIRouter | None:
        from app.modules.gamification.api import router

        return router

    def get_models(self) -> list:
        return [GamificationEvent, UserPoints, Badge, UserBadge, LeaderboardEntry]

    def get_dependencies(self) -> list[str]:
        return ["auth", "users", "pubsub", "tasks"]

    @property
    def module_name(self) -> str:
        return "Gamificación"

    @property
    def description(self) -> str:
        return "Sistema de gamificación: puntos, niveles, badges, streaks y leaderboards."


def create_module(db: Session | None = None) -> GamificationModule:
    return GamificationModule(db)
