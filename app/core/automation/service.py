"""Automation service for rule management."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.automation import AutomationExecutionStatus, Rule
from app.repositories.automation_repository import AutomationRepository

logger = logging.getLogger(__name__)


class AutomationService:
    """Service for automation rule management."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = AutomationRepository(db)

    def create_rule(
        self,
        tenant_id: UUID,
        name: str,
        trigger: dict[str, Any],
        actions: list[dict[str, Any]],
        description: str | None = None,
        conditions: list[dict[str, Any]] | None = None,
        enabled: bool = True,
    ) -> Rule:
        """Create a new automation rule.

        Args:
            tenant_id: Tenant ID
            name: Rule name
            trigger: Trigger configuration (event or time)
            actions: List of actions to execute
            description: Rule description (optional)
            conditions: List of conditions (optional)
            enabled: Whether rule is enabled

        Returns:
            Created rule
        """
        rule_data = {
            "tenant_id": tenant_id,
            "name": name,
            "description": description,
            "enabled": enabled,
            "trigger": trigger,
            "conditions": conditions or [],
            "actions": actions,
        }
        rule = self.repository.create_rule(rule_data)

        # Create initial version
        self.repository.create_rule_version(
            {
                "rule_id": rule.id,
                "version": 1,
                "definition": {
                    "name": name,
                    "description": description,
                    "trigger": trigger,
                    "conditions": conditions or [],
                    "actions": actions,
                },
            }
        )

        logger.info(f"Created rule '{name}' (ID: {rule.id}) for tenant {tenant_id}")
        return rule

    def get_rule(self, rule_id: UUID, tenant_id: UUID) -> Rule | None:
        """Get a rule by ID.

        Args:
            rule_id: Rule ID
            tenant_id: Tenant ID

        Returns:
            Rule or None if not found
        """
        return self.repository.get_rule_by_id(rule_id, tenant_id)

    def get_all_rules(
        self, tenant_id: UUID, enabled_only: bool = False, skip: int = 0, limit: int = 100
    ) -> list[Rule]:
        """Get all rules for a tenant.

        Args:
            tenant_id: Tenant ID
            enabled_only: Only return enabled rules
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of rules
        """
        return self.repository.get_all_rules(tenant_id, enabled_only, skip, limit)

    def update_rule(
        self,
        rule_id: UUID,
        tenant_id: UUID,
        name: str | None = None,
        description: str | None = None,
        trigger: dict[str, Any] | None = None,
        conditions: list[dict[str, Any]] | None = None,
        actions: list[dict[str, Any]] | None = None,
        enabled: bool | None = None,
    ) -> Rule | None:
        """Update a rule.

        Args:
            rule_id: Rule ID
            tenant_id: Tenant ID
            name: New name (optional)
            description: New description (optional)
            trigger: New trigger (optional)
            conditions: New conditions (optional)
            actions: New actions (optional)
            enabled: New enabled status (optional)

        Returns:
            Updated rule or None if not found
        """
        rule = self.repository.get_rule_by_id(rule_id, tenant_id)
        if not rule:
            return None

        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if trigger is not None:
            update_data["trigger"] = trigger
        if conditions is not None:
            update_data["conditions"] = conditions
        if actions is not None:
            update_data["actions"] = actions
        if enabled is not None:
            update_data["enabled"] = enabled

        updated_rule = self.repository.update_rule(rule_id, tenant_id, update_data)

        # Create new version if rule definition changed
        if trigger is not None or conditions is not None or actions is not None:
            latest_version = self.repository.get_latest_version(rule_id)
            new_version = (latest_version.version + 1) if latest_version else 1
            self.repository.create_rule_version(
                {
                    "rule_id": rule_id,
                    "version": new_version,
                    "definition": {
                        "name": updated_rule.name,
                        "description": updated_rule.description,
                        "trigger": updated_rule.trigger,
                        "conditions": updated_rule.conditions or [],
                        "actions": updated_rule.actions,
                    },
                }
            )

        logger.info(f"Updated rule {rule_id} for tenant {tenant_id}")
        return updated_rule

    def delete_rule(self, rule_id: UUID, tenant_id: UUID) -> bool:
        """Delete a rule.

        Args:
            rule_id: Rule ID
            tenant_id: Tenant ID

        Returns:
            True if deleted, False if not found
        """
        result = self.repository.delete_rule(rule_id, tenant_id)
        if result:
            logger.info(f"Deleted rule {rule_id} for tenant {tenant_id}")
        return result

    def get_executions(
        self, rule_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AutomationExecutionStatus]:
        """Get execution history for a rule.

        Args:
            rule_id: Rule ID
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of executions
        """
        return self.repository.get_executions_by_rule(rule_id, skip, limit)


