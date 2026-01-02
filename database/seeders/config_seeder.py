"""Configuration seeder for default module configurations.

Creates default configuration values for business modules.
This seeder is idempotent - it will not create duplicate configurations.
"""

from sqlalchemy.orm import Session
from uuid import UUID

from app.core.seeders.base import Seeder
from app.models.system_config import SystemConfig
from app.models.tenant import Tenant


class ConfigSeeder(Seeder):
    """Seeder for default module configurations.

    Creates default configuration values for:
    - products: pricing and discount settings
    - inventory: stock alerts and warehouse settings
    - sales: payment terms and quotes
    - purchases: approval workflows

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
            self._seed_tenant_config(db, tenant.id)

    def _seed_tenant_config(self, db: Session, tenant_id: UUID) -> None:
        """Seed configuration for a specific tenant.

        Args:
            db: Database session
            tenant_id: Tenant ID
        """
        # Default configurations for each module
        default_configs = {
            "products": {
                "min_price": 0.0,
                "max_price": 999999.99,
                "currency": "USD",
                "enable_discounts": True,
                "default_tax_rate": 0.16,
                "enable_variants": False,
                "auto_sku": True,
            },
            "inventory": {
                "enable_stock_alerts": True,
                "low_stock_threshold": 10,
                "enable_multi_warehouse": False,
                "default_warehouse": "main",
                "enable_batch_tracking": False,
            },
            "sales": {
                "default_payment_terms": 30,
                "enable_quotes": True,
                "quote_expiry_days": 30,
                "require_approval_above": 10000.0,
                "default_discount_type": "percentage",
            },
            "purchases": {
                "require_approval": True,
                "approval_threshold": 5000.0,
                "default_payment_terms": 30,
                "enable_purchase_orders": True,
            },
        }

        for module, configs in default_configs.items():
            for key, value in configs.items():
                # Check if config already exists
                existing = (
                    db.query(SystemConfig)
                    .filter(
                        SystemConfig.tenant_id == tenant_id,
                        SystemConfig.module == module,
                        SystemConfig.key == key,
                    )
                    .first()
                )

                if not existing:
                    config = SystemConfig(
                        tenant_id=tenant_id,
                        module=module,
                        key=key,
                        value=value,
                    )
                    db.add(config)

        db.commit()
        print(f"✅ ConfigSeeder: Default configurations created for tenant {tenant_id}")













