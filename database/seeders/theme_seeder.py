"""Theme seeder for default visual configuration.

Creates default theme configuration (colors, logos, fonts, styles).
This seeder is idempotent - it will not create duplicate configurations.
"""

from sqlalchemy.orm import Session
from uuid import UUID

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
            "primary_color": "#1976D2",  # Material Blue 700
            "secondary_color": "#DC004E",  # Material Pink 700
            "accent_color": "#FFC107",  # Material Amber 500
            "background_color": "#FFFFFF",
            "surface_color": "#F5F5F5",
            # Status colors
            "error_color": "#F44336",  # Material Red 500
            "warning_color": "#FF9800",  # Material Orange 500
            "success_color": "#4CAF50",  # Material Green 500
            "info_color": "#2196F3",  # Material Blue 500
            # Text colors
            "text_primary": "#212121",  # Material Grey 900
            "text_secondary": "#757575",  # Material Grey 600
            "text_disabled": "#BDBDBD",  # Material Grey 400
            # Logos (default paths - tenants can override)
            "logo_primary": "/assets/logos/logo.png",
            "logo_white": "/assets/logos/logo-white.png",
            "logo_small": "/assets/logos/logo-sm.png",
            "logo_name": "/assets/logos/logo-name.png",
            "favicon": "/assets/logos/favicon.ico",
            "login_background": "/assets/images/login-bg.jpg",
            # Typography
            "font_family_primary": "Roboto",
            "font_family_secondary": "Arial",
            "font_family_monospace": "Courier New",
            "font_size_base": "14px",
            "font_size_small": "12px",
            "font_size_large": "16px",
            "font_size_heading": "24px",
            # Component styles
            "sidebar_bg": "#2C3E50",  # Dark Blue Grey
            "sidebar_text": "#ECF0F1",  # Light Grey
            "navbar_bg": "#34495E",  # Midnight Blue
            "navbar_text": "#FFFFFF",
            "button_radius": "4px",
            "card_radius": "8px",
            "input_radius": "4px",
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
        print(f"✅ ThemeSeeder: Default theme configuration created for tenant {tenant_id}")













