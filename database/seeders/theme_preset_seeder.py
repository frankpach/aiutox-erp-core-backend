"""Theme preset seeder for creating default theme presets."""

from sqlalchemy.orm import Session

from app.core.config.service import ConfigService
from app.core.seeders.base import Seeder
from app.models.tenant import Tenant
from app.models.theme_preset import ThemePreset


class ThemePresetSeeder(Seeder):
    """Seeder for creating default theme presets.

    Creates the "Original" system preset for each tenant.
    This seeder is idempotent - it will not create duplicate presets.
    """

    # Default theme configuration (Original theme)
    DEFAULT_THEME_CONFIG = {
        "primary_color": "#023E87",
        "secondary_color": "#F1F5F9",
        "accent_color": "#F1F5F9",
        "background_color": "#FFFFFF",
        "surface_color": "#FFFFFF",
        "error_color": "#EF4444",
        "warning_color": "#F59E0B",
        "success_color": "#10B981",
        "info_color": "#3B82F6",
        "text_primary": "#0F172A",
        "text_secondary": "#64748B",
        "text_disabled": "#94A3B8",
        "sidebar_bg": "#FAFAFA",
        "sidebar_text": "#0F172A",
        "navbar_bg": "#FFFFFF",
        "navbar_text": "#0F172A",
        "logo_primary": "/assets/logos/logo.png",
        "logo_white": "/assets/logos/logo-white.png",
        "logo_small": "/assets/logos/logo-sm.png",
        "logo_name": "/assets/logos/logo-name.png",
        "favicon": "/favicon.ico",
        "login_background": "",
        "font_family_primary": "Manrope",
        "font_family_secondary": "Arial",
        "font_family_monospace": "Courier New",
        "font_size_base": "14px",
        "font_size_small": "12px",
        "font_size_large": "18px",
        "font_size_heading": "24px",
        "button_radius": "0.25rem",
        "card_radius": "0.5rem",
        "input_radius": "0.25rem",
        "shadow_elevation_1": "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)",
        "shadow_elevation_2": "0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23)",
        "shadow_elevation_3": "0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23)",
    }

    def run(self, db: Session) -> None:
        """Run the seeder.

        Creates the "Original" system preset for each tenant.
        Also sets it as the active theme if no theme config exists.

        Args:
            db: Database session
        """
        # Get all tenants
        tenants = db.query(Tenant).all()

        if not tenants:
            # No tenants exist yet, skip
            return

        config_service = ConfigService(db)

        for tenant in tenants:
            # Check if "Original" preset already exists for this tenant
            existing_preset = (
                db.query(ThemePreset)
                .filter(
                    ThemePreset.tenant_id == tenant.id,
                    ThemePreset.is_system == True,
                    ThemePreset.name == "Original",
                )
                .first()
            )

            if existing_preset:
                # Preset already exists, skip
                continue

            # Create "Original" preset
            preset = ThemePreset(
                tenant_id=tenant.id,
                name="Original",
                description="Theme original del sistema",
                config=self.DEFAULT_THEME_CONFIG,
                is_default=True,
                is_system=True,
                created_by=None,  # System preset
            )
            db.add(preset)
            db.commit()
            db.refresh(preset)

            # If no theme config exists for this tenant, set the default theme as active
            theme_config = config_service.get_module_config(
                tenant_id=tenant.id, module="app_theme"
            )

            if not theme_config:
                # Set default theme as active
                config_service.set_module_config(
                    tenant_id=tenant.id,
                    module="app_theme",
                    config_dict=self.DEFAULT_THEME_CONFIG,
                    user_id=None,  # System
                    ip_address=None,
                    user_agent=None,
                )
                db.commit()










