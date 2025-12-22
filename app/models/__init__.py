from app.core.db.session import Base
from app.core.seeders.models import SeederRecord
from app.models.contact import Contact
from app.models.contact_method import ContactMethod
from app.models.audit_log import AuditLog
from app.models.delegated_permission import DelegatedPermission
from app.models.module_role import ModuleRole
from app.models.organization import Organization
from app.models.person_identification import PersonIdentification
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_role import UserRole
# Products models are now loaded dynamically via ModuleRegistry
# Do not import them here to avoid circular imports
from app.models.system_config import SystemConfig
from app.models.automation import AutomationExecution, Rule, RuleVersion
from app.models.preference import Dashboard, OrgPreference, RolePreference, SavedView, UserPreference
from app.models.reporting import DashboardWidget, ReportDefinition
from app.models.notification import NotificationQueue, NotificationTemplate
from app.models.file import File, FilePermission, FileVersion
from app.models.activity import Activity
from app.models.tag import EntityTag, Tag, TagCategory
from app.models.task import (
    Task,
    TaskChecklistItem,
    Workflow,
    WorkflowExecution,
    WorkflowStep,
)
from app.models.search_index import SearchIndex
from app.models.integration import (
    Integration,
    Webhook,
    WebhookDelivery,
    WebhookStatus,
)

__all__ = [
    "Activity",
    "EntityTag",
    "AuditLog",
    "AutomationExecution",
    "Base",
    "Contact",
    "ContactMethod",
    "Dashboard",
    "DashboardWidget",
    "DelegatedPermission",
    "File",
    "FilePermission",
    "FileVersion",
    "Integration",
    "ModuleRole",
    "Webhook",
    "WebhookDelivery",
    "WebhookStatus",
    "NotificationQueue",
    "NotificationTemplate",
    "OrgPreference",
    "Organization",
    "PersonIdentification",
    # Products models (Category, Product, ProductBarcode, ProductVariant) are now
    # loaded dynamically via ModuleRegistry - do not include them here
    "RefreshToken",
    "ReportDefinition",
    "RolePreference",
    "Rule",
    "RuleVersion",
    "SavedView",
    "SearchIndex",
    "SeederRecord",
    "SystemConfig",
    "Tag",
    "TagCategory",
    "Task",
    "TaskChecklistItem",
    "Tenant",
    "User",
    "UserPreference",
    "UserRole",
    "Workflow",
    "WorkflowExecution",
    "WorkflowStep",
]

