"""RBAC permissions for crm module."""

from __future__ import annotations

CRM_VIEW = "crm.view"
CRM_MANAGE = "crm.manage"
CRM_LEADS_MANAGE = "crm.leads.manage"
CRM_OPPORTUNITIES_MANAGE = "crm.opportunities.manage"

CRM_PERMISSIONS = [
    CRM_VIEW,
    CRM_MANAGE,
    CRM_LEADS_MANAGE,
    CRM_OPPORTUNITIES_MANAGE,
]
