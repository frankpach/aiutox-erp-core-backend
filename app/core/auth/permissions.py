"""Permission definitions and verification utilities for RBAC."""

# Permisos globales del sistema
GLOBAL_PERMISSIONS = {
    "auth.manage_users",  # Gestionar usuarios de la organización
    "auth.manage_roles",  # Gestionar roles globales
    "auth.view_audit",  # Ver logs de auditoría
    "system.configure",  # Configurar sistema
    "system.view_reports",  # Ver reportes globales
}

# Mapeo de roles globales a permisos
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "*",  # Acceso total a todos los permisos
    },
    "admin": {
        # Permisos globales
        "auth.manage_users",
        "auth.manage_roles",
        "auth.view_audit",
        "system.configure",
        "system.view_reports",
        # Permisos de módulos (wildcard para todos los módulos)
        "*.*.view",  # Ver todos los módulos
        "*.*.edit",  # Editar todos los módulos
        "*.*.delete",  # Eliminar en todos los módulos
        "*.*.manage_users",  # Gestionar usuarios de todos los módulos
    },
    "manager": {
        # Permisos globales limitados
        "system.view_reports",
        # Permisos de módulos (se asignan por módulo específico)
        # Los managers pueden tener permisos delegados por módulo
    },
    "staff": {
        # Permisos básicos de visualización
        "system.view_reports",
        # Los staff reciben permisos delegados por módulo
    },
    "viewer": {
        # Solo lectura global
        "system.view_reports",
        # Ver todos los módulos (solo lectura)
        "*.*.view",
    },
}

# Mapeo de roles internos de módulo a permisos
# Formato: MODULE_ROLES[module][role_name] = set[permissions]
# El role_name se almacena sin el prefijo "internal." en la base de datos
# pero se usa con el prefijo "internal." en el código para claridad
MODULE_ROLES: dict[str, dict[str, set[str]]] = {
    "inventory": {
        "internal.editor": {
            "inventory.view",
            "inventory.edit",
            "inventory.adjust_stock",
        },
        "internal.viewer": {
            "inventory.view",
        },
        "internal.manager": {
            "inventory.view",
            "inventory.edit",
            "inventory.adjust_stock",
            "inventory.manage_users",  # Permite delegar permisos
        },
    },
    "products": {
        "internal.editor": {
            "products.view",
            "products.edit",
            "products.create",
        },
        "internal.viewer": {
            "products.view",
        },
        "internal.manager": {
            "products.view",
            "products.edit",
            "products.create",
            "products.delete",
            "products.manage_users",  # Permite delegar permisos
        },
    },
    "config": {
        "internal.viewer": {"config.view"},
        "internal.editor": {"config.view", "config.edit"},
        "internal.manager": {
            "config.view",
            "config.edit",
            "config.delete",
        },
    },
    "calendar": {
        "internal.viewer": {"calendar.view", "calendar.events.view"},
        "internal.editor": {
            "calendar.view",
            "calendar.events.view",
            "calendar.events.manage",
        },
        "internal.manager": {
            "calendar.view",
            "calendar.manage",
            "calendar.events.view",
            "calendar.events.manage",
        },
    },
    "import_export": {
        "internal.viewer": {"import_export.view"},
        "internal.importer": {"import_export.view", "import_export.import"},
        "internal.exporter": {"import_export.view", "import_export.export"},
        "internal.manager": {
            "import_export.view",
            "import_export.manage",
            "import_export.import",
            "import_export.export",
        },
    },
    "views": {
        "internal.viewer": {"views.view"},
        "internal.editor": {"views.view", "views.manage"},
        "internal.manager": {
            "views.view",
            "views.manage",
            "views.share",
        },
    },
    "approvals": {
        "internal.viewer": {"approvals.view"},
        "internal.approver": {"approvals.view", "approvals.approve"},
        "internal.manager": {
            "approvals.view",
            "approvals.manage",
            "approvals.approve",
            "approvals.delegate",
        },
    },
    "templates": {
        "internal.viewer": {"templates.view"},
        "internal.editor": {"templates.view", "templates.manage", "templates.render"},
        "internal.manager": {
            "templates.view",
            "templates.manage",
            "templates.render",
        },
    },
    "comments": {
        "internal.viewer": {"comments.view"},
        "internal.creator": {"comments.view", "comments.create"},
        "internal.editor": {"comments.view", "comments.create", "comments.edit"},
        "internal.manager": {
            "comments.view",
            "comments.create",
            "comments.edit",
            "comments.delete",
            "comments.manage",
        },
    },
    # Más módulos se agregarán según se implementen
    # Ejemplo futuro:
    # "orders": {
    #     "internal.editor": {"orders.view", "orders.edit", "orders.create"},
    #     "internal.viewer": {"orders.view"},
    #     "internal.manager": {"orders.view", "orders.edit", "orders.create", "orders.manage_users"},
    # },
    # "reporting": {
    #     "internal.viewer": {"reporting.view"},
    #     "internal.editor": {"reporting.view", "reporting.create", "reporting.edit"},
    #     "internal.manager": {"reporting.view", "reporting.create", "reporting.edit", "reporting.delete", "reporting.manage_users"},
    # },
    # "notifications": {
    #     "internal.viewer": {"notifications.view"},
    #     "internal.editor": {"notifications.view", "notifications.create", "notifications.edit"},
    #     "internal.manager": {"notifications.view", "notifications.create", "notifications.edit", "notifications.delete", "notifications.manage_users"},
    # },
}

# Documentación: Cómo agregar nuevos módulos
# ===========================================
# Para agregar un nuevo módulo al sistema:
#
# 1. Agregar entrada en MODULE_ROLES con la estructura:
#    "module_name": {
#        "internal.viewer": {"module_name.view"},
#        "internal.editor": {"module_name.view", "module_name.edit", "module_name.create"},
#        "internal.manager": {"module_name.view", "module_name.edit", "module_name.create", "module_name.delete", "module_name.manage_users"},
#    }
#
# 2. Seguir las convenciones de permisos:
#    - Formato: {module}.{action}
#    - Acciones estándar: view, edit, create, delete, manage_users
#
# 3. Ver documentación completa en: docs/ai-prompts/modules/module-setup-guide.md
#
# 4. Usar el template en docs/ai-prompts/backend-template.md para generar el código del módulo


def has_permission(user_permissions: set[str], required: str) -> bool:
    """
    Check if user has the required permission using exact and wildcard matching.

    Wildcard matching rules:
    1. Exact match: "inventory.view" matches "inventory.view"
    2. Module wildcard: "inventory.*" matches "inventory.view", "inventory.edit", etc.
    3. Action wildcard: "*.view" matches "inventory.view", "products.view", etc.
    4. Total wildcard: "*" or "*.*" matches all permissions

    Args:
        user_permissions: Set of permission strings the user has.
        required: Required permission string to check.

    Returns:
        True if user has the required permission, False otherwise.

    Examples:
        >>> has_permission({"inventory.view"}, "inventory.view")
        True
        >>> has_permission({"inventory.*"}, "inventory.edit")
        True
        >>> has_permission({"*.view"}, "products.view")
        True
        >>> has_permission({"*"}, "inventory.edit")
        True
    """
    # 1. Exact match
    if required in user_permissions:
        return True

    # 2. Wildcard match: "inventory.*" permite "inventory.view", "inventory.edit", etc.
    for perm in user_permissions:
        if perm.endswith(".*"):
            prefix = perm[:-2]  # Remover ".*"
            if required.startswith(prefix + "."):
                return True

    # 3. Wildcard match: "*.view" permite "inventory.view", "products.view", etc.
    for perm in user_permissions:
        if perm.startswith("*."):
            suffix = perm[2:]  # Remover "*."
            if required.endswith("." + suffix):
                return True

    # 3b. Wildcard match: "*.*.view" permite "inventory.view", "products.view", etc.
    # Formato: *.*.action (módulo y acción wildcard)
    for perm in user_permissions:
        if perm.startswith("*.*."):
            suffix = perm[4:]  # Remover "*.*."
            if required.endswith("." + suffix):
                return True

    # 4. Wildcard total: "*" o "*.*" permite todos los permisos
    if "*" in user_permissions or "*.*" in user_permissions:
        return True

    return False

