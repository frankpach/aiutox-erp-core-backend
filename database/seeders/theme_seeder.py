"""Theme seeder for default visual configuration.

Creates default theme configuration (colors, logos, fonts, styles).
This seeder is idempotent - it will not create duplicate configurations.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.seeders.base import Seeder
from app.models.system_config import SystemConfig
from app.models.tenant import Tenant


class ThemeSeeder(Seeder):
    """Seeder for default visual theme configuration.

    Creates default configuration values for the app_theme module:
    - Color scheme (primary, secondary, accent, text, backgrounds)
    - Logo paths (primary, white, small, favicon)
    - Typography (fonts and sizes)
    - Component styles (sidebar, navbar, buttons, cards)

    This seeder is idempotent - it will not create duplicate configurations.
    """

    def run(self, db: Session) -> None:
        """Run the seeder.

        Args:
            db: Database session
        """
        # Get all tenants
        tenants = db.query(Tenant).all()

        for tenant in tenants:
            self._seed_tenant_theme(db, tenant.id)

    def _seed_tenant_theme(self, db: Session, tenant_id: UUID) -> None:
        """Seed theme configuration for a specific tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID
        """
        # Default theme configuration
        default_theme = {
            # Main colors
            "primary_color": "#023E87",
            "secondary_color": "#F1F5F9",
            "accent_color": "#F1F5F9",
            "background_color": "#FFFFFF",
            "surface_color": "#FFFFFF",
            # Status colors
            "error_color": "#EF4444",
            "warning_color": "#F59E0B",
            "success_color": "#10B981",
            "info_color": "#3B82F6",
            # Text colors
            "text_primary": "#0F172A",
            "text_secondary": "#64748B",
            "text_disabled": "#94A3B8",
            # Logos (default paths - tenants can override)
            "logo_primary": "/assets/logos/logo.png",
            "logo_white": "/assets/logos/logo-white.png",
            "logo_small": "/assets/logos/logo-sm.png",
            "logo_name": "/assets/logos/logo-name.png",
            "favicon": "/favicon.ico",
            "login_background": "",
            # Typography
            "font_family_primary": "Manrope",
            "font_family_secondary": "Arial",
            "font_family_monospace": "Courier New",
            "font_size_base": "14px",
            "font_size_small": "12px",
            "font_size_large": "18px",
            "font_size_heading": "24px",
            # Component styles
            "sidebar_bg": "#FAFAFA",
            "sidebar_text": "#0F172A",
            "navbar_bg": "#FFFFFF",
            "navbar_text": "#0F172A",
            "button_radius": "0.25rem",
            "card_radius": "0.5rem",
            "input_radius": "0.25rem",
            # Shadows
            "shadow_elevation_1": "0 2px 4px rgba(0,0,0,0.1)",
            "shadow_elevation_2": "0 4px 8px rgba(0,0,0,0.15)",
            "shadow_elevation_3": "0 8px 16px rgba(0,0,0,0.2)",
        }

        for key, value in default_theme.items():
            # Check if theme config already exists
            existing = (
                db.query(SystemConfig)
                .filter(
                    SystemConfig.tenant_id == tenant_id,
                    SystemConfig.module == "app_theme",
                    SystemConfig.key == key,
                )
                .first()
            )

            if not existing:
                config = SystemConfig(
                    tenant_id=tenant_id,
                    module="app_theme",
                    key=key,
                    value=value,
                )
                db.add(config)

        db.commit()
        print(
            f"✅ ThemeSeeder: Default theme configuration created for tenant {tenant_id}"
        )
