# Scripts de Ejecución de Tests - Pub-Sub Module

## 🚀 Ejecución Rápida

### Opción 1: Script Bash (Recomendado)
```bash
cd backend
bash scripts/run_pubsub_tests.sh
```

### Opción 2: Ejecución Manual con uv
```bash
cd backend

# Tests unitarios
uv run pytest tests/unit/test_pubsub_client.py \
             tests/unit/test_pubsub_publisher.py \
             tests/unit/test_pubsub_consumer.py \
             tests/unit/test_pubsub_models.py \
             tests/unit/test_pubsub_errors.py \
             tests/unit/test_pubsub_groups.py \
             tests/unit/test_pubsub_retry.py \
             -v --tb=short

# Tests de integración (requieren Redis)
uv run pytest tests/integration/test_pubsub_integration.py -v --tb=short -m "redis"

# Tests de API
uv run pytest tests/api/test_pubsub_api.py -v --tb=short
```

### Opción 3: Ejecutar todos los tests del proyecto
```bash
cd backend
bash scripts/run_all_tests.sh
```

## 📋 Archivos de Test

### Tests Unitarios (7 archivos)
- `tests/unit/test_pubsub_client.py` - Cliente Redis Streams
- `tests/unit/test_pubsub_publisher.py` - Publicador de eventos
- `tests/unit/test_pubsub_consumer.py` - Consumidor de eventos
- `tests/unit/test_pubsub_models.py` - Modelos Pydantic
- `tests/unit/test_pubsub_errors.py` - Excepciones personalizadas
- `tests/unit/test_pubsub_groups.py` - Gestión de grupos
- `tests/unit/test_pubsub_retry.py` - Lógica de reintentos

### Tests de Integración (1 archivo)
- `tests/integration/test_pubsub_integration.py` - Tests con Redis real

### Tests de API (1 archivo)
- `tests/api/test_pubsub_api.py` - Endpoints de la API

## ⚙️ Opciones de pytest

- `-v` o `--verbose`: Salida detallada
- `--tb=short`: Traceback corto en errores
- `--maxfail=N`: Detener después de N fallos
- `-m "redis"`: Ejecutar solo tests marcados con `@pytest.mark.redis`
- `-x`: Detener en el primer fallo
- `-k "pattern"`: Ejecutar solo tests que coincidan con el patrón

## 🔧 Solución de Problemas

### Error: "No module named 'pydantic_settings'"
```bash
cd backend
uv sync --extra dev
```

### Error: "Redis is not available"
Los tests de integración se saltan automáticamente si Redis no está disponible.
Para ejecutarlos, asegúrate de que Redis esté corriendo:
```bash
# Verificar que Redis está corriendo
docker ps | grep redis
# O
redis-cli ping
```

### Tests se cuelgan
Si un test se cuelga, usa timeout:
```bash
timeout 30 uv run pytest tests/unit/test_pubsub_consumer.py::test_consume_loop_processes_messages -v
```

## 📊 Resultados Esperados

### Tests Unitarios
- **Total**: 57 tests
- **Esperado**: Todos pasando ✅

### Tests de Integración
- **Total**: 4 tests
- **Esperado**: Todos pasando si Redis está disponible, o se saltan si no está

### Tests de API
- **Total**: 3 tests
- **Esperado**: Todos pasando (pueden saltarse si falta permiso `pubsub.view`)

## 🐛 Si Encuentras Errores

1. **Ejecuta el test específico que falla:**
   ```bash
   uv run pytest tests/unit/test_pubsub_client.py::test_redis_client_connection_failure -v
   ```

2. **Verifica el traceback completo:**
   ```bash
   uv run pytest tests/unit/test_pubsub_client.py::test_redis_client_connection_failure -v --tb=long
   ```

3. **Ejecuta con más información:**
   ```bash
   uv run pytest tests/unit/test_pubsub_client.py::test_redis_client_connection_failure -v -s
   ```

## 💡 Cómo Ayudar

Si encuentras problemas al ejecutar los tests:

1. **Comparte el error completo:**
   - Copia toda la salida del comando
   - Incluye el traceback completo

2. **Información del entorno:**
   - Sistema operativo
   - Versión de Python: `python --version`
   - Versión de uv: `uv --version`
   - Si Redis está corriendo: `docker ps | grep redis`

3. **Test específico que falla:**
   - Nombre del test
   - Archivo donde está
   - Mensaje de error

4. **Si un test se cuelga:**
   - Presiona `Ctrl+C` para cancelarlo
   - Ejecuta solo ese test con timeout
   - Comparte qué estaba haciendo cuando se colgó



