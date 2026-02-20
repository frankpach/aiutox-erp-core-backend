"""Automation repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.automation import AutomationExecution, Rule, RuleVersion


class AutomationRepository:
    """Repository for automation data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Rule operations
    def create_rule(self, rule_data: dict) -> Rule:
        """Create a new rule."""
        rule = Rule(**rule_data)
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def get_rule_by_id(self, rule_id: UUID, tenant_id: UUID) -> Rule | None:
        """Get rule by ID and tenant ID."""
        return (
            self.db.query(Rule)
            .filter(Rule.id == rule_id, Rule.tenant_id == tenant_id)
            .first()
        )

    def get_all_rules(
        self,
        tenant_id: UUID,
        enabled_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Rule]:
        """Get all rules by tenant with pagination."""
        query = self.db.query(Rule).filter(Rule.tenant_id == tenant_id)
        if enabled_only:
            query = query.filter(Rule.enabled)
        return query.offset(skip).limit(limit).all()

    def count_all_rules(self, tenant_id: UUID, enabled_only: bool = False) -> int:
        """Count all rules by tenant."""
        from sqlalchemy import func

        query = self.db.query(func.count(Rule.id)).filter(Rule.tenant_id == tenant_id)
        if enabled_only:
            query = query.filter(Rule.enabled)
        return query.scalar() or 0

    def update_rule(
        self, rule_id: UUID, tenant_id: UUID, rule_data: dict
    ) -> Rule | None:
        """Update a rule."""
        rule = self.get_rule_by_id(rule_id, tenant_id)
        if not rule:
            return None
        for key, value in rule_data.items():
            setattr(rule, key, value)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: UUID, tenant_id: UUID) -> bool:
        """Delete a rule."""
        rule = self.get_rule_by_id(rule_id, tenant_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True

    # RuleVersion operations
    def create_rule_version(self, version_data: dict) -> RuleVersion:
        """Create a new rule version."""
        version = RuleVersion(**version_data)
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_rule_versions(self, rule_id: UUID) -> list[RuleVersion]:
        """Get all versions for a rule."""
        return (
            self.db.query(RuleVersion)
            .filter(RuleVersion.rule_id == rule_id)
            .order_by(RuleVersion.version.desc())
            .all()
        )

    def get_latest_version(self, rule_id: UUID) -> RuleVersion | None:
        """Get the latest version for a rule."""
        return (
            self.db.query(RuleVersion)
            .filter(RuleVersion.rule_id == rule_id)
            .order_by(RuleVersion.version.desc())
            .first()
        )

    # AutomationExecution operations
    def create_execution(self, execution_data: dict) -> AutomationExecution:
        """Create a new automation execution record."""
        execution = AutomationExecution(**execution_data)
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        return execution

    def get_execution_by_event_id(self, event_id: UUID) -> AutomationExecution | None:
        """Get execution by event ID (for idempotency check)."""
        return (
            self.db.query(AutomationExecution)
            .filter(AutomationExecution.event_id == event_id)
            .first()
        )

    def get_executions_by_rule(
        self, rule_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[AutomationExecution]:
        """Get all executions for a rule."""
        return (
            self.db.query(AutomationExecution)
            .filter(AutomationExecution.rule_id == rule_id)
            .order_by(AutomationExecution.executed_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_executions_by_rule(self, rule_id: UUID) -> int:
        """Count all executions for a rule."""
        from sqlalchemy import func

        return (
            self.db.query(func.count(AutomationExecution.id))
            .filter(AutomationExecution.rule_id == rule_id)
            .scalar()
            or 0
        )
