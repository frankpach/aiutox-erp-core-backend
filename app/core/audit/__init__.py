"""Audit core module namespace."""

from app.core.module_interface import ModuleInterface, ModuleNavigationItem


class AuditCoreModule(ModuleInterface):
    """Core audit module metadata for dynamic navigation."""

    @property
    def module_id(self) -> str:
        return "audit"

    @property
    def module_type(self) -> str:
        return "core"

    @property
    def enabled(self) -> bool:
        return True

    def get_settings_navigation(self) -> list[ModuleNavigationItem]:
        return [
            ModuleNavigationItem(
                id="audit.logs",
                label="Auditoría",
                path="/config/audit",
                permission="auth.view_audit",
                icon="settings",
                category="Configuración",
                order=80,
            )
        ]


def create_module(_db: object | None = None) -> AuditCoreModule:
    return AuditCoreModule()


__all__ = ["AuditCoreModule", "create_module"]
