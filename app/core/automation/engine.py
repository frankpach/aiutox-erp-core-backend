"""Automation engine for executing rules."""

import logging

from sqlalchemy.orm import Session

from app.core.automation.action_executor import ActionExecutor
from app.core.automation.condition_evaluator import ConditionEvaluator
from app.core.pubsub.models import Event
from app.models.automation import AutomationExecution, AutomationExecutionStatus, Rule
from app.repositories.automation_repository import AutomationRepository

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Engine for executing automation rules."""

    def __init__(self, db: Session):
        """Initialize automation engine.

        Args:
            db: Database session
        """
        self.db = db
        self.repository = AutomationRepository(db)
        self.condition_evaluator = ConditionEvaluator()
        self.action_executor = ActionExecutor(db)

    async def execute_rule(self, rule: Rule, event: Event) -> AutomationExecution:
        """Execute a rule for a given event.

        Args:
            rule: Rule to execute
            event: Triggering event

        Returns:
            AutomationExecution record
        """
        # Check idempotency: has this rule already processed this event?
        existing_execution = self.repository.get_execution_by_rule_and_event(
            rule.id, event.event_id
        )
        if existing_execution:
            logger.info(
                f"Event {event.event_id} already processed by rule {rule.id}, skipping"
            )
            return existing_execution

        # Check if rule is enabled
        if not rule.enabled:
            logger.debug(f"Rule {rule.id} is disabled, skipping")
            execution = self.repository.create_execution(
                {
                    "rule_id": rule.id,
                    "event_id": event.event_id,
                    "status": AutomationExecutionStatus.SKIPPED,
                    "result": {"reason": "rule_disabled"},
                }
            )
            return execution

        # Evaluate conditions if any
        if rule.conditions:
            conditions_met = self.condition_evaluator.evaluate(rule.conditions, event)
            if not conditions_met:
                logger.debug(
                    f"Conditions not met for rule {rule.id} with event {event.event_id}"
                )
                execution = self.repository.create_execution(
                    {
                        "rule_id": rule.id,
                        "event_id": event.event_id,
                        "status": AutomationExecutionStatus.SKIPPED,
                        "result": {"reason": "conditions_not_met"},
                    }
                )
                return execution

        # Execute actions
        try:
            result = await self.action_executor.execute(rule.actions, event)
            execution = self.repository.create_execution(
                {
                    "rule_id": rule.id,
                    "event_id": event.event_id,
                    "status": AutomationExecutionStatus.SUCCESS,
                    "result": result,
                }
            )
            logger.info(
                f"Successfully executed rule {rule.id} for event {event.event_id}"
            )
            return execution
        except Exception as e:
            logger.error(
                f"Failed to execute rule {rule.id} for event {event.event_id}: {e}",
                exc_info=True,
            )
            execution = self.repository.create_execution(
                {
                    "rule_id": rule.id,
                    "event_id": event.event_id,
                    "status": AutomationExecutionStatus.FAILED,
                    "error_message": str(e),
                    "result": None,
                }
            )
            return execution

    async def process_event(self, event: Event) -> list[AutomationExecution]:
        """Process an event by executing all matching rules.

        Args:
            event: Event to process

        Returns:
            List of execution records
        """
        # Get all enabled rules for the tenant
        rules = self.repository.get_all_rules(
            tenant_id=event.tenant_id, enabled_only=True
        )

        executions = []
        for rule in rules:
            # Check if rule matches event type
            trigger = rule.trigger
            if trigger.get("type") == "event":
                event_type = trigger.get("event_type")
                if event_type and event.event_type == event_type:
                    execution = await self.execute_rule(rule, event)
                    executions.append(execution)

        return executions
