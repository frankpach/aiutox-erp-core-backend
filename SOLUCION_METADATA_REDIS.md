# Solución Definitiva: Problema de metadata_source en Redis

## Problema Identificado

El test `test_event_metadata_preserved` fallaba porque:
1. **Hay mensajes antiguos en Redis** con `metadata_source: 'unknown'` (de tests anteriores)
2. **Los grupos de consumidores se crean con `start_id="0"`** por defecto, lo que hace que lean desde el principio del stream
3. **El consumer lee mensajes antiguos** antes de llegar al nuevo mensaje con `metadata_source: 'test_service'`

## Solución Implementada

### 1. ✅ Limpieza Automática de Streams (Fixture)

Se agregó un fixture `clean_redis_streams` que:
- **Limpia los streams** antes de cada test (elimina mensajes antiguos)
- **Elimina grupos de consumidores de test** para que se puedan recrear con el `start_id` correcto
- Se ejecuta automáticamente antes de cada test (`autouse=True`)

```python
@pytest.fixture(autouse=True)
async def clean_redis_streams(redis_client):
    """Clean Redis streams and consumer groups before each test."""
    # Limpia streams y grupos antes de cada test
```

### 2. ✅ Soporte para `start_id="$"` en Consumer

Se modificó `EventConsumer.subscribe()` para aceptar:
- `start_id`: ID inicial del grupo (por defecto `"0"` para todos los mensajes)
- `recreate_group`: Si `True`, elimina y recrea el grupo si ya existe

**Uso en tests:**
```python
await event_consumer.subscribe(
    group_name="test-group",
    consumer_name="test-consumer",
    event_types=["product.updated"],
    callback=callback,
    start_id="$",  # Solo lee mensajes nuevos (después de este punto)
    recreate_group=True,  # Recrea el grupo para asegurar el start_id correcto
)
```

### 3. ✅ Mejoras en `create_group()`

Se agregó el parámetro `recreate_if_exists`:
- Si `True`, elimina el grupo existente y lo recrea con el nuevo `start_id`
- Útil para tests donde necesitas asegurar que el grupo empiece desde un punto específico

### 4. ✅ Mejoras en Manejo de Datos

El código ya maneja correctamente diferentes formatos de datos de Redis:
- Dict (cuando `decode_responses=True`)
- List/Tuple (formato alternativo de Redis)
- Conversión automática a dict

## Archivos Modificados

1. **`app/core/pubsub/consumer.py`**
   - Agregado parámetro `start_id` y `recreate_group` a `subscribe()`

2. **`app/core/pubsub/client.py`**
   - Agregado parámetro `recreate_if_exists` a `create_group()`

3. **`app/core/pubsub/groups.py`**
   - Agregado parámetro `recreate_if_exists` a `ensure_group_exists()`

4. **`tests/integration/test_pubsub_integration.py`**
   - Agregado fixture `clean_redis_streams` (autouse)
   - Actualizado tests para usar `start_id="$"` y `recreate_group=True`

## Verificación

### Test Individual:
```bash
uv run --extra dev pytest tests/integration/test_pubsub_integration.py::test_event_metadata_preserved -v
```
✅ **Pasa correctamente**

### Tests en Paralelo:
```bash
uv run --extra dev pytest tests/integration/test_pubsub_integration.py -n 4 -v
```
✅ **Todos los tests pasan**

## Comportamiento de `start_id` en Redis

- **`start_id="0"`** (default): Lee todos los mensajes desde el principio del stream
- **`start_id="$"`**: Lee solo mensajes nuevos (después de crear el grupo)
- **`start_id="<id>"`**: Lee desde un ID específico

## Limpieza Manual de Redis (Si es Necesario)

Si necesitas limpiar Redis manualmente:

```bash
# Usando el script
cd backend
uv run python scripts/check_redis_streams.py clean

# O usando redis-cli directamente
redis-cli DEL events:domain
redis-cli DEL events:technical
redis-cli DEL events:failed
```

## Prevención Futura

1. **El fixture `clean_redis_streams`** se ejecuta automáticamente antes de cada test
2. **Los tests usan `start_id="$"`** para leer solo mensajes nuevos
3. **Los grupos se recrean** con `recreate_group=True` para asegurar el `start_id` correcto

## Resultado

✅ **Problema resuelto definitivamente**
- Los tests ya no leen mensajes antiguos
- El metadata se preserva correctamente
- Funciona en ejecuciones individuales y paralelas














