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
# Ejecutar todos los tests
uv run pytest

# Con cobertura
uv run pytest --cov=app --cov-report=html
```

### Migraciones

```bash
# Crear nueva migración
uv run alembic revision --autogenerate -m "descripción"

# Aplicar migraciones
uv run alembic upgrade head

# Revertir última migración
uv run alembic downgrade -1
```

## API Documentation

Una vez iniciado el servidor:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

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

