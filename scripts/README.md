# Scripts de Desarrollo

Esta carpeta contiene todos los scripts de desarrollo y utilidades del proyecto.

## Estructura

### `cli/`
CLI unificado `aiutox` con todas las herramientas de desarrollo.

**Comandos principales:**
- `aiutox migrate:*` - Gestión de migraciones
- `aiutox make:*` - Generadores de código
- `aiutox db:*` - Base de datos y seeders
- `aiutox test:*` - Testing
- `aiutox route:*` - Rutas
- `aiutox analyze:*` - Análisis de código
- `aiutox repl:*` - REPL interactivo

**Ver documentación completa**: `docs/ai-prompts/cli-guide.md`

### `diagnostics/`
Scripts de diagnóstico para verificar y diagnosticar problemas con la base de datos y el sistema.

**Scripts disponibles:**
- `check_postgres_simple.py` - Verificación simple de conexión (pytest)
- `diagnose_postgres.py` - Diagnóstico completo de PostgreSQL
- `test_db_connection_simple.py` - Prueba de conexión y encoding

**Ver**: `scripts/diagnostics/README.md`

### `utils/`
Scripts de utilidad para desarrollo y mantenimiento.

**Scripts disponibles:**
- `fix_env_encoding.py` - Corregir problemas de encoding en `.env`

**Ver**: `scripts/utils/README.md`

### Scripts Principales

- `migrate_cli.py` - CLI interactivo de migraciones (legacy, usar `aiutox migrate` en su lugar)
- `verify_migrations.py` - Script independiente de verificación de migraciones

## Uso

### CLI Unificado (Recomendado)

```bash
# Ver ayuda general
aiutox --help

# Migraciones
aiutox migrate apply
aiutox migrate status
aiutox migrate verify

# Generadores
aiutox make:model Product
aiutox make:module Order

# Seeders
aiutox make:seeder UserSeeder
aiutox db:seed

# Testing
aiutox test:run
aiutox test:coverage
```

### Scripts de Diagnóstico

```bash
# Verificar conexión a PostgreSQL
uv run python scripts/diagnostics/check_postgres_simple.py

# Diagnóstico completo
uv run python scripts/diagnostics/diagnose_postgres.py
```

### Scripts de Utilidad

```bash
# Corregir encoding de .env
uv run python scripts/utils/fix_env_encoding.py
```

## Notas

- **Preferir `aiutox`** sobre scripts directos cuando sea posible
- Los scripts en `temp/` son temporales y no están versionados
- Los scripts de diagnóstico son herramientas de desarrollo, no usar en producción

