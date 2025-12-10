# Backend - AiutoX ERP

Backend FastAPI para el sistema AiutoX ERP.

## Requisitos

- Python 3.12+
- `uv` (Package Manager)
- PostgreSQL 16
- Redis 7+

## Setup

1. Instalar dependencias:
   ```bash
   uv sync
   ```

2. Configurar variables de entorno:
   ```bash
   cp .env.example .env
   # Editar .env con tus configuraciones
   ```

3. Ejecutar migraciones:
   ```bash
   # Usando el CLI unificado (recomendado)
   uv run aiutox migrate apply

   # O usando el CLI interactivo original
   python scripts/migrate_cli.py migrate
   python scripts/migrate_cli.py  # Modo interactivo

   # O usando Alembic directamente
   uv run alembic upgrade head
   ```

4. Iniciar servidor de desarrollo:
   ```bash
   uv run fastapi dev app/main.py
   ```

   O con uvicorn directamente:
   ```bash
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Estructura

- `app/api/v1/`: Routers REST por módulo
- `app/core/`: Configuración, auth, base de datos
- `app/models/`: Modelos SQLAlchemy
- `app/schemas/`: Schemas Pydantic (Request/Response)
- `app/repositories/`: Capa de acceso a datos
- `app/services/`: Lógica de negocio
- `app/tasks/`: Tareas asíncronas (Celery - fase 2)
- `migrations/`: Migraciones Alembic
- `tests/`: Tests con pytest
- `scripts/`: Scripts de desarrollo
  - `cli/`: CLI unificado (`aiutox`)
  - `utils/`: Scripts de utilidad
  - `diagnostics/`: Scripts de diagnóstico
- `database/seeders/`: Seeders de base de datos
- `temp/`: Scripts temporales de verificación (no versionados)

## Desarrollo

### Formateo y Linting

```bash
# Formatear código
uv run black .
uv run isort .

# Verificar sin cambios
uv run black --check .
uv run isort --check .

# Linting
uv run ruff check .
```

### Tests

```bash
# Usando CLI unificado (recomendado)
uv run --extra dev aiutox test run
uv run --extra dev aiutox test run --coverage
uv run --extra dev aiutox test watch
uv run --extra dev aiutox test coverage

# O directamente con pytest
uv run --extra dev pytest -v
uv run --extra dev pytest --cov=app --cov-report=html --cov-report=term

# Ejecutar tests específicos
uv run --extra dev pytest tests/unit/test_auth_*.py -v
uv run --extra dev pytest tests/integration/test_auth_*.py -v
```

**Nota**: Los tests requieren las dependencias de desarrollo (`--extra dev`). El CLI maneja esto automáticamente.

Para más información sobre testing, ver:
- [Documentación de Tests de Autenticación](../docs/modules/auth-testing.md)
- [Rules de Testing](../rules/tests.md)

### CLI Unificado (aiutox)

El proyecto incluye un CLI unificado `aiutox` con todas las herramientas de desarrollo.

**Nota importante**: El comando `aiutox` debe ejecutarse con `uv run` ya que está instalado como script del proyecto:

```bash
# Ver ayuda general
uv run aiutox --help

# Migraciones
uv run aiutox migrate apply              # Aplicar migraciones pendientes
uv run aiutox migrate status             # Ver estado actual
uv run aiutox migrate verify             # Verificar BD vs archivos
uv run aiutox migrate rollback --steps 1 # Revertir migraciones (con confirmación)
uv run aiutox migrate fresh --yes        # Drop todas las tablas y re-migrar
uv run aiutox migrate refresh --yes      # Rollback + migrate
uv run aiutox migrate make "descripción" # Crear nueva migración
uv run aiutox migrate history            # Ver historial
uv run aiutox migrate interactive         # Modo interactivo completo

# Seeders
uv run aiutox make:seeder UserSeeder     # Crear nuevo seeder
uv run aiutox db:seed                    # Ejecutar todos los seeders
uv run aiutox db:seed --class=UserSeeder # Ejecutar seeder específico
uv run aiutox db:seed:rollback           # Revertir último seeder
uv run aiutox db:reset --yes             # Reset completo (fresh + seed)

# Generadores de código
uv run aiutox make:model Product         # Generar modelo
uv run aiutox make:service Product      # Generar servicio
uv run aiutox make:repository Product   # Generar repositorio
uv run aiutox make:router Product        # Generar router
uv run aiutox make:schema Product        # Generar schema
uv run aiutox make:module Order --entities=Order,OrderItem  # Generar módulo completo

# Base de datos
uv run aiutox db:check                   # Verificar conexión y estado

# Testing (requiere --extra dev)
uv run --extra dev aiutox test:run                   # Ejecutar tests
uv run --extra dev aiutox test:run --coverage         # Con cobertura
uv run --extra dev aiutox test:watch                  # Modo watch
uv run --extra dev aiutox test:coverage               # Reporte de cobertura

# Rutas
uv run aiutox route:list                 # Listar todas las rutas de la API

# REPL interactivo
uv run aiutox repl start                  # IPython con contexto de la app

# Análisis de código
uv run aiutox analyze:complexity          # Análisis de complejidad
uv run aiutox analyze:security            # Auditoría de seguridad
uv run aiutox analyze:dependencies        # Vulnerabilidades en dependencias
```

### Migraciones

#### CLI Unificado (Recomendado)

```bash
# Aplicar migraciones
uv run aiutox migrate apply

# Ver estado
uv run aiutox migrate status

# Verificar
uv run aiutox migrate verify

# Rollback (mejorado con confirmación)
uv run aiutox migrate rollback --steps 1
uv run aiutox migrate rollback --steps 2 --yes  # Sin confirmación

# Crear migración
uv run aiutox migrate make "descripción"
```

#### CLI Interactivo Original

El proyecto también incluye el CLI interactivo original:

```bash
# Modo interactivo (menú)
python scripts/migrate_cli.py

# Modo no-interactivo (comandos)
python scripts/migrate_cli.py migrate
python scripts/migrate_cli.py status
python scripts/migrate_cli.py verify
python scripts/migrate_cli.py rollback [--steps N]
python scripts/migrate_cli.py fresh --yes
python scripts/migrate_cli.py refresh --yes
python scripts/migrate_cli.py make:migration "descripción"
```

#### Comandos Alembic Directos (Alternativa)

También puedes usar Alembic directamente:

```bash
# Crear nueva migración
uv run alembic revision --autogenerate -m "descripción"

# Aplicar migraciones
uv run alembic upgrade head

# Revertir última migración
uv run alembic downgrade -1
```

#### Verificación de Migraciones

El CLI incluye verificaciones automáticas:

- **Verificar estado**: Compara migraciones aplicadas en BD vs archivos
- **Verificar esquema**: Compara modelos SQLAlchemy vs esquema real de BD
- **Verificar integridad**: Valida cadena de migraciones

```bash
python scripts/migrate_cli.py verify
```

#### Ejemplos de Uso

**Aplicar migraciones pendientes:**
```bash
python scripts/migrate_cli.py migrate
```

**Ver estado detallado:**
```bash
python scripts/migrate_cli.py status
```

**Crear nueva migración:**
```bash
python scripts/migrate_cli.py make:migration "add_user_preferences_table"
```

**Rollback de última migración:**
```bash
python scripts/migrate_cli.py rollback
```

**Rollback de múltiples migraciones:**
```bash
python scripts/migrate_cli.py rollback --steps 3
```

## Autenticación y RBAC

El sistema incluye un sistema completo de autenticación y control de acceso basado en roles (RBAC):

### Roles Globales
- **owner**: Acceso total (`*`)
- **admin**: Gestión completa con permisos de módulos (`*.*.view`, `*.*.edit`, etc.)
- **manager**: Permisos básicos, puede recibir permisos delegados
- **staff**: Permisos mínimos, puede recibir permisos delegados
- **viewer**: Solo lectura (`*.*.view`)

### Roles Internos de Módulo
Los módulos pueden definir roles internos para simplificar la gestión de permisos:

- **Formato**: `internal.<role_name>` (ej: `internal.editor`, `internal.viewer`, `internal.manager`)
- **Ejemplo para Inventory**:
  - `internal.editor` → `["inventory.view", "inventory.edit", "inventory.adjust_stock"]`
  - `internal.viewer` → `["inventory.view"]`
  - `internal.manager` → `["inventory.view", "inventory.edit", "inventory.adjust_stock", "inventory.manage_users"]`

Los roles internos se asignan a usuarios específicos por módulo y se combinan con los roles globales para calcular los permisos efectivos.

### Uso de Dependencies de Autorización

```python
from app.core.auth.dependencies import require_permission, require_roles, require_any_permission

# Requerir un permiso específico
@router.get("/items")
async def list_items(
    user: User = Depends(require_permission("inventory.view")),
    db: Session = Depends(get_db)
):
    ...

# Requerir uno o más roles
@router.get("/admin/users")
async def list_users(
    user: User = Depends(require_roles("admin", "owner")),
    db: Session = Depends(get_db)
):
    ...

# Requerir cualquiera de varios permisos
@router.get("/data")
async def get_data(
    user: User = Depends(require_any_permission("inventory.view", "products.view")),
    db: Session = Depends(get_db)
):
    ...
```

### Wildcard Matching

El sistema soporta wildcards en permisos:
- `inventory.*` - Todos los permisos del módulo inventory
- `*.view` - Ver en todos los módulos
- `*.*.view` - Ver en todos los módulos (formato completo)
- `*` - Todos los permisos (solo owner)

Para más información, ver:
- [Rules de Auth & RBAC](../rules/auth-rbac.md)
- [Plan de Implementación](../docs/ai-prompts/auth/backend-plan.md)

## API Documentation

Una vez iniciado el servidor:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Todos los endpoints están documentados automáticamente con:
- Descripciones y ejemplos
- Códigos de error documentados
- Schemas de request/response

## Docker

```bash
# Desarrollo
docker compose -f docker-compose.dev.yml up --build
```

## Reglas y Estándares

Ver documentación en `rules/`:
- `naming.md`: Convenciones de nombres
- `dev-style.md`: Estilo de desarrollo
- `api-contract.md`: Contrato de API
- `tests.md`: Estándares de testing

## Documentación Adicional

- **CLI Unificado**: `docs/ai-prompts/cli-guide.md` - Guía completa del CLI `aiutox`
- **Migraciones**: `docs/12-migrations.md` - Sistema de migraciones detallado

