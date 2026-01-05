# Diagnóstico: Problema de metadata_source en Redis

## Problema Reportado

El test `test_event_metadata_preserved` falla con:
```
AssertionError: assert 'unknown' == 'test_service'
```

## Investigación Realizada

### 1. Verificación del Flujo de Datos

**Publicación (Publisher):**
- ✅ `to_redis_dict()` guarda correctamente `metadata_source: 'test_service'`
- ✅ El evento se publica correctamente a Redis

**Lectura (Consumer):**
- ✅ Redis devuelve los datos correctamente: `metadata_source: 'test_service'`
- ✅ `from_redis_dict()` recibe los datos correctamente
- ✅ El evento se parsea correctamente con `metadata.source: 'test_service'`

### 2. Debug Realizado

Se agregaron prints de debug que mostraron:
```
[DEBUG CONSUMER] metadata_source value: 'test_service'
[DEBUG CONSUMER] Parsed event.metadata.source: 'test_service'
[DEBUG TEST] Event 0: metadata.source = 'test_service'
```

**El test pasa correctamente** cuando se ejecuta individualmente.

## Posibles Causas

### 1. Eventos Antiguos en Redis (Más Probable)

Si hay mensajes antiguos en el stream de Redis que no tienen `metadata_source`, el consumer podría estar leyendo esos mensajes en lugar del nuevo.

**Solución:** Limpiar los streams de Redis antes de ejecutar los tests.

### 2. Problema de Race Condition

En ejecuciones paralelas, múltiples tests podrían estar interfiriendo entre sí.

**Solución:** Usar grupos de consumidores únicos por test.

### 3. Problema de Formato de Datos de Redis

Aunque `decode_responses=True`, Redis podría devolver los datos en formato diferente en algunos casos.

**Solución:** Ya implementada - el código maneja tanto dict como list/tuple.

## Información Necesaria de Redis

Para diagnosticar completamente, necesitamos:

1. **Verificar streams en Redis:**
   ```bash
   # Conectar a Redis
   redis-cli

   # Ver mensajes en el stream
   XRANGE events:domain - + COUNT 10

   # Ver si hay mensajes sin metadata_source
   XRANGE events:domain - + COUNT 100 | grep -v metadata_source
   ```

2. **Verificar grupos de consumidores:**
   ```bash
   XINFO GROUPS events:domain
   XINFO CONSUMERS events:domain test-group-2
   ```

3. **Limpiar streams si es necesario:**
   ```bash
   # Eliminar todos los mensajes del stream (CUIDADO: esto borra todo)
   XDEL events:domain <message-id>
   # O eliminar el stream completo
   DEL events:domain
   ```

## Correcciones Aplicadas

1. ✅ Mejorado el manejo de datos en `consumer.py` para soportar múltiples formatos
2. ✅ Verificado que `from_redis_dict()` maneja correctamente los datos
3. ✅ El código ahora es más robusto ante diferentes formatos de Redis

## Próximos Pasos

1. **Limpiar Redis:** Eliminar mensajes antiguos de los streams
2. **Verificar configuración:** Asegurar que `decode_responses=True` está activo
3. **Ejecutar test en aislamiento:** Verificar que no hay interferencia de otros tests

## Comandos para Verificar Redis

```bash
# Ver todos los streams
redis-cli KEYS "events:*"

# Ver mensajes en un stream
redis-cli XRANGE events:domain - + COUNT 20

# Ver información del stream
redis-cli XINFO STREAM events:domain

# Ver grupos de consumidores
redis-cli XINFO GROUPS events:domain

# Limpiar un stream específico (CUIDADO)
redis-cli DEL events:domain
```





















