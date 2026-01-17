# Setup Guide - Teams Module

## Descripción

Este documento describe cómo configurar y aplicar las migraciones para el módulo de Teams (equipos y grupos) en AiutoX ERP.

## Fecha de Implementación

**2026-01-16** - Fase 1.1: Asignación a Grupos

---

## 🚀 Pasos de Configuración

### 1. Aplicar Migración de Base de Datos

```powershell
# Navegar al directorio backend
cd backend

# Aplicar la migración
alembic upgrade head
```

**Migración aplicada**: `2026_01_16-add_teams_tables.py`

**Tablas creadas**:

- `teams` - Equipos/grupos con soporte de jerarquía
- `team_members` - Relación usuario-equipo

**Modificaciones**:

- `task_assignments` - Agregados constraints de exclusividad

---

### 2. Verificar Migración

```powershell
# Verificar que las tablas existen
psql -d aiutox_erp -c "\dt teams*"

# Verificar constraints
psql -d aiutox_erp -c "\d+ task_assignments"
```

**Salida esperada**:

```
                    List of relations
 Schema |     Name      | Type  |  Owner
--------+---------------+-------+----------
 public | teams         | table | postgres
 public | team_members  | table | postgres

Check constraints:
    "check_assignment_exclusive" CHECK (assigned_to_id IS NULL OR assigned_to_group_id IS NULL)
    "check_assignment_target" CHECK (assigned_to_id IS NOT NULL OR assigned_to_group_id IS NOT NULL)
```

---

### 3. Registrar Módulo en la Aplicación

El módulo ya está registrado en:

- `backend/app/models/__init__.py` - Modelos exportados
- `backend/app/modules/teams/` - Módulo completo

**Verificar imports**:

```python
from app.models.team import Team, TeamMember
from app.services.team_service import TeamService
```

---

### 4. Configurar Permisos

Agregar los siguientes permisos al sistema:

```python
# Permisos del módulo Teams
TEAMS_PERMISSIONS = [
    "teams.view",      # Ver equipos
    "teams.manage",    # Crear/editar/eliminar equipos
    "teams.assign",    # Asignar miembros a equipos
]
```

**Archivo**: `backend/app/core/auth/permissions.py` (si existe)

---

### 5. Ejecutar Tests

```powershell
# Tests unitarios de TeamService
pytest tests/services/test_team_service.py -v

# Tests de integración (cuando estén disponibles)
pytest tests/integration/test_teams_api.py -v
```

---

## 📋 Endpoints Disponibles

### Teams CRUD

| Método | Endpoint                  | Descripción       | Permiso        |
| ------ | ------------------------- | ----------------- | -------------- |
| POST   | `/api/v1/teams`           | Crear equipo      | `teams.manage` |
| GET    | `/api/v1/teams`           | Listar equipos    | `teams.view`   |
| GET    | `/api/v1/teams/{team_id}` | Obtener equipo    | `teams.view`   |
| PUT    | `/api/v1/teams/{team_id}` | Actualizar equipo | `teams.manage` |
| DELETE | `/api/v1/teams/{team_id}` | Eliminar equipo   | `teams.manage` |

### Team Members

| Método | Endpoint                                    | Descripción           | Permiso        |
| ------ | ------------------------------------------- | --------------------- | -------------- |
| POST   | `/api/v1/teams/{team_id}/members`           | Agregar miembro       | `teams.manage` |
| GET    | `/api/v1/teams/{team_id}/members`           | Listar miembros       | `teams.view`   |
| DELETE | `/api/v1/teams/{team_id}/members/{user_id}` | Remover miembro       | `teams.manage` |
| GET    | `/api/v1/teams/{team_id}/members/resolved`  | Obtener IDs resueltos | `teams.view`   |

### Task Assignments

| Método | Endpoint                                              | Descripción         | Permiso        |
| ------ | ----------------------------------------------------- | ------------------- | -------------- |
| POST   | `/api/v1/tasks/{task_id}/assignments`                 | Asignar tarea       | `tasks.assign` |
| GET    | `/api/v1/tasks/{task_id}/assignments`                 | Listar asignaciones | `tasks.view`   |
| DELETE | `/api/v1/tasks/{task_id}/assignments/{assignment_id}` | Eliminar asignación | `tasks.assign` |

---

## 🧪 Ejemplos de Uso

### Crear un Equipo

```bash
curl -X POST http://localhost:8000/api/v1/teams \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Equipo de Desarrollo",
    "description": "Equipo principal de desarrollo",
    "color": "#3b82f6",
    "is_active": true
  }'
```

### Agregar Miembro a Equipo

```bash
curl -X POST http://localhost:8000/api/v1/teams/{team_id}/members \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": "{team_id}",
    "user_id": "{user_id}",
    "role": "member"
  }'
```

### Asignar Tarea a Grupo

```bash
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "{task_id}",
    "assigned_to_group_id": "{team_id}",
    "role": "owner",
    "notes": "Asignado al equipo completo"
  }'
```

---

## 🔍 Verificación de Funcionalidad

### 1. Verificar Visibilidad por Grupos

```python
from app.services.team_service import TeamService
from app.repositories.task_repository import TaskRepository

# Obtener grupos del usuario
team_service = TeamService(db)
user_groups = team_service.get_user_groups(tenant_id, user_id)

# Obtener tareas visibles
task_repo = TaskRepository(db)
visible_tasks = task_repo.get_tasks_with_group_visibility(
    tenant_id=tenant_id,
    user_id=user_id,
    user_group_ids=user_groups,
)

print(f"Usuario pertenece a {len(user_groups)} grupos")
print(f"Puede ver {len(visible_tasks)} tareas")
```

### 2. Verificar Jerarquías

```python
# Crear equipo padre e hijo
parent_team = Team(tenant_id=tenant_id, name="Padre")
child_team = Team(tenant_id=tenant_id, name="Hijo", parent_team_id=parent_team.id)

# Agregar miembros
team_service.add_team_member(tenant_id, parent_team.id, user1_id, admin_id)
team_service.add_team_member(tenant_id, child_team.id, user2_id, admin_id)

# Obtener miembros con anidación
all_members = team_service.get_group_members(
    tenant_id,
    parent_team.id,
    include_nested=True
)

print(f"Total de miembros (incluyendo hijos): {len(all_members)}")
```

---

## ⚠️ Notas Importantes

1. **Constraints de Exclusividad**: Una asignación solo puede tener `assigned_to_id` O `assigned_to_group_id`, no ambos.

2. **Validación en Dos Capas**:
    - Base de datos: CheckConstraints de PostgreSQL
    - Aplicación: Validadores Pydantic

3. **Performance**: Los índices compuestos optimizan queries de visibilidad.

4. **Jerarquías**: Las jerarquías de equipos son opcionales y recursivas.

5. **Caché**: Considerar implementar caché de membresías con Redis para mejor performance.

---

## 🐛 Troubleshooting

### Error: "Debe asignar a un usuario o grupo"

**Causa**: Intentando crear asignación sin `assigned_to_id` ni `assigned_to_group_id`.

**Solución**: Proporcionar al menos uno de los dos campos.

### Error: "No puede asignar a usuario y grupo simultáneamente"

**Causa**: Intentando asignar a ambos en la misma asignación.

**Solución**: Crear dos asignaciones separadas si es necesario.

### Error: "Team not found"

**Causa**: El team_id no existe o pertenece a otro tenant.

**Solución**: Verificar que el equipo existe y pertenece al tenant correcto.

---

## 📚 Referencias

- Documentación de modelos: `backend/app/models/team.py`
- Servicio de equipos: `backend/app/services/team_service.py`
- Endpoints API: `backend/app/modules/teams/api.py`
- Tests: `backend/tests/services/test_team_service.py`
- Plan de implementación: `.windsurf/plans/01-16-2026_implementation_plan.md`

---

**Última actualización**: 2026-01-16
**Estado**: ✅ Listo para uso
**Versión**: 1.0.0
