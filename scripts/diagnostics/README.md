# Scripts de Diagnóstico

Scripts para verificar y diagnosticar problemas con la base de datos y el sistema.

## Scripts Disponibles

### `check_postgres.py`
Script simple para verificar conexión a PostgreSQL desde CMD.

**Uso:**
```bash
uv run python scripts/diagnostics/check_postgres.py
```

### `check_postgres_simple.py`
Prueba simple para verificar conexión a PostgreSQL (versión pytest).

**Uso:**
```bash
uv run pytest scripts/diagnostics/check_postgres_simple.py -v -s
```

### `diagnose_postgres.py`
Script de diagnóstico completo para PostgreSQL en Windows.

**Uso:**
```bash
uv run python scripts/diagnostics/diagnose_postgres.py
```

### `test_db_connection_simple.py`
Script simple para probar conexión a base de datos y diagnosticar problemas de encoding.

**Uso:**
```bash
uv run python scripts/diagnostics/test_db_connection_simple.py
```

## Nota

Para verificaciones más completas de la base de datos, ver `temp/README.md` que contiene scripts más detallados.

