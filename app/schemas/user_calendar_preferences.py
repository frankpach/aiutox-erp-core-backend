"""User Calendar Preferences Schemas.

Sprint 5 - Fase 2
"""

from pydantic import BaseModel, ConfigDict, Field


class UserCalendarPreferencesBase(BaseModel):
    """Base schema para preferencias de calendario."""

    auto_sync_enabled: bool = Field(
        default=False, description="Auto-sincronización habilitada"
    )
    default_calendar_provider: str = Field(
        default="internal", description="Proveedor de calendario por defecto"
    )
    timezone: str = Field(
        default="America/Mexico_City", description="Zona horaria del usuario"
    )
    time_format: str = Field(default="24h", description="Formato de hora (24h o 12h)")


class UserCalendarPreferencesCreate(UserCalendarPreferencesBase):
    """Schema para crear preferencias."""

    pass


class UserCalendarPreferencesUpdate(BaseModel):
    """Schema para actualizar preferencias."""

    auto_sync_enabled: bool | None = None
    default_calendar_provider: str | None = None
    timezone: str | None = None
    time_format: str | None = None


class UserCalendarPreferencesResponse(UserCalendarPreferencesBase):
    """Schema de respuesta de preferencias."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: str
    updated_at: str
