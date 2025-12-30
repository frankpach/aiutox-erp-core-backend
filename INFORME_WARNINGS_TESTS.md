# Informe de Warnings en las Pruebas del Backend

**Fecha:** 2025-12-19
**Total de Tests:** 775 ✅
**Total de Warnings:** 529 ⚠️
**Workers:** 16
**Tiempo de Ejecución:** ~47-49 segundos

---

## Resumen Ejecutivo

Las pruebas del backend se ejecutan correctamente (775 tests pasando), pero hay 529 warnings que se pueden categorizar en 6 tipos principales. La mayoría son **warnings de deprecación** que no afectan la funcionalidad actual, pero deberían corregirse para mantener el código actualizado y evitar problemas futuros.

---

## Categorías de Warnings

### 1. PytestCollectionWarning: `test_router` (16 warnings)

**Ubicación:** `starlette/routing.py:712`

**Problema:**
```python
PytestCollectionWarning: cannot collect 'test_router' because it is not a function.
    async def __call__(self, scope: Scope, receive: Send, send: Send) -> None:
```

**Causa:**
- Pytest intenta recopilar funciones que comienzan con `test_` como tests
- Starlette tiene un método `__call__` en su router que pytest interpreta incorrectamente
- No es un problema del código del proyecto, sino de cómo pytest interactúa con Starlette

**Impacto:** ⚠️ Bajo - No afecta la funcionalidad, solo ruido en los logs

**Solución:**
- Agregar a `pytest.ini` o `pyproject.toml`:
  ```ini
  [tool.pytest.ini_options]
  filterwarnings = [
      "ignore::pytest.PytestCollectionWarning:starlette.routing"
  ]
  ```

---

### 2. SAWarning: Transaction Already Deassociated (Múltiples)

**Ubicación:** `tests/conftest.py:271`

**Problema:**
```python
SAWarning: transaction already deassociated from connection
    transaction.rollback()
```

**Causa:**
- En el fixture `db_session`, se intenta hacer rollback de una transacción que ya fue desasociada de la conexión
- Esto ocurre cuando la transacción ya fue cerrada o cuando hay múltiples intentos de rollback
- Afecta a varios tests que usan el fixture `db_session`

**Tests Afectados:**
- `test_activities_service.py::test_create_activity`
- `test_security_multi_tenant.py::test_calendar_tenant_isolation`
- `test_import_export_service.py::test_create_import_job`
- `test_tasks_service.py::test_delete_task`
- `test_tasks_service.py::test_get_tasks`
- Y otros...

**Impacto:** ⚠️ Medio - No afecta la funcionalidad pero indica un problema en el manejo de transacciones

**Solución:**
- Mejorar el manejo de excepciones en `conftest.py`:
  ```python
  try:
      db.rollback()
      transaction.rollback()
  except Exception as e:
      # Verificar si la transacción ya fue cerrada
      if "already deassociated" not in str(e):
          print(f"[DB CLEANUP] Warning during rollback: {e}")
  ```

---

### 3. DeprecationWarning: `asyncio.get_event_loop()` (Múltiples)

**Ubicación:** `app/core/pubsub/event_helpers.py:54`

**Problema:**
```python
DeprecationWarning: There is no current event loop
    loop = asyncio.get_event_loop()
```

**Causa:**
- `asyncio.get_event_loop()` está deprecado en Python 3.10+
- Debe usarse `asyncio.get_running_loop()` cuando hay un loop corriendo, o `asyncio.new_event_loop()` cuando no
- El código intenta obtener un loop que no existe en el contexto actual

**Tests Afectados:**
- `test_error_handling.py::test_calendar_invalid_data`
- `test_error_handling.py::test_validation_error_format`
- `test_role_management.py::test_assign_role_invalid_role`

**Impacto:** ⚠️ Medio - Funciona pero usará APIs deprecadas que pueden desaparecer

**Solución:**
```python
# En event_helpers.py, línea 54
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
```

---

### 4. DeprecationWarning: `HTTP_422_UNPROCESSABLE_ENTITY` (Múltiples)

**Ubicación:** `starlette/_exception_handler.py:59`

**Problema:**
```python
DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated.
Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
```

**Causa:**
- Starlette/FastAPI está usando una constante HTTP deprecada
- No es código del proyecto, sino de la librería Starlette
- Se activa cuando se retornan errores de validación (422)

**Tests Afectados:** Todos los tests que generan errores de validación (muchos)

**Impacto:** ⚠️ Bajo - Es un problema de la librería, se resolverá cuando Starlette actualice

**Solución:**
- Esperar actualización de Starlette/FastAPI
- O usar un filtro de warnings:
  ```ini
  filterwarnings = [
      "ignore::DeprecationWarning:starlette._exception_handler"
  ]
  ```

---

### 5. DeprecationWarning: `datetime.utcnow()` (Múltiples)

**Ubicación:**
- `app/core/files/service.py:70`
- `tests/integration/test_calendar_integration.py:78, 79, 128, 129`

**Problema:**
```python
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal
in a future version. Use timezone-aware objects to represent datetimes in UTC:
datetime.datetime.now(datetime.UTC).
```

**Causa:**
- `datetime.utcnow()` está deprecado en Python 3.12+
- Debe usarse `datetime.now(datetime.UTC)` para obtener datetimes con timezone

**Archivos Afectados:**
1. `app/core/files/service.py:70`
   ```python
   now = datetime.utcnow()  # ❌ Deprecado
   ```
   Debe ser:
   ```python
   from datetime import UTC
   now = datetime.now(UTC)  # ✅ Correcto
   ```

2. `tests/integration/test_calendar_integration.py:78, 79, 128, 129`
   ```python
   start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()  # ❌
   ```
   Debe ser:
   ```python
   from datetime import UTC
   start_time = (datetime.now(UTC) + timedelta(days=1)).isoformat()  # ✅
   ```

**Impacto:** ⚠️ Medio - Funciona ahora pero dejará de funcionar en futuras versiones de Python

**Solución:** Reemplazar todas las instancias de `datetime.utcnow()` con `datetime.now(UTC)`

---

### 6. PytestCacheWarning: Permisos de Cache (2 warnings)

**Ubicación:** `.pytest_cache/v/cache/`

**Problema:**
```python
PytestCacheWarning: could not create cache path
D:\Documents\Mis_proyectos\Proyectos_Actuales\aiutox_erp_core\backend\.pytest_cache\v\cache\nodeids:
[WinError 5] Access is denied
```

**Causa:**
- Pytest no puede escribir en el directorio de cache debido a permisos de Windows
- Puede ser por permisos de archivo o porque el directorio está bloqueado por otro proceso

**Impacto:** ⚠️ Bajo - No afecta la ejecución de tests, solo el cache (que acelera ejecuciones futuras)

**Solución:**
- Verificar permisos del directorio `.pytest_cache`
- O ejecutar pytest con permisos de administrador
- O agregar a `.gitignore` y recrear el directorio

---

## Distribución de Warnings por Archivo

### Tests con Más Warnings:

1. **test_products.py:** 22 warnings
2. **test_auth_service.py:** 18 warnings
3. **test_auth_endpoints.py:** 16 warnings
4. **test_permission_delegation.py:** 15 warnings
5. **test_rbac.py:** 14 warnings
6. **test_user_management.py:** 14 warnings
7. **test_user_repository.py:** 14 warnings
8. **test_permission_repository.py:** 14 warnings
9. **test_config.py:** 12 warnings
10. **test_config_service.py:** 11 warnings

### Tests Unitarios vs Integración:

- **Unit Tests:** ~150 warnings
- **Integration Tests:** ~350 warnings
- **Otros (API, CLI):** ~29 warnings

---

## Recomendaciones Prioritarias

### 🔴 Alta Prioridad (Afectan funcionalidad futura):

1. **Reemplazar `datetime.utcnow()`** (5 instancias)
   - `app/core/files/service.py:70`
   - `tests/integration/test_calendar_integration.py` (4 instancias)

2. **Corregir `asyncio.get_event_loop()`** (1 instancia)
   - `app/core/pubsub/event_helpers.py:54`

### 🟡 Media Prioridad (Mejoran calidad del código):

3. **Mejorar manejo de transacciones en conftest.py**
   - Prevenir warnings de SQLAlchemy sobre transacciones desasociadas

4. **Agregar filtros de warnings en pyproject.toml**
   - Filtrar warnings de librerías externas (Starlette)

### 🟢 Baja Prioridad (Solo limpieza):

5. **Resolver permisos de cache de pytest**
   - Mejorar velocidad de ejecuciones futuras

---

## Plan de Acción Sugerido

### Fase 1: Correcciones Críticas (1-2 horas)
- [ ] Reemplazar `datetime.utcnow()` en todos los archivos
- [ ] Corregir `asyncio.get_event_loop()` en `event_helpers.py`

### Fase 2: Mejoras de Calidad (2-3 horas)
- [ ] Mejorar manejo de transacciones en `conftest.py`
- [ ] Agregar filtros de warnings en `pyproject.toml`

### Fase 3: Optimizaciones (1 hora)
- [ ] Resolver permisos de cache de pytest
- [ ] Documentar cambios realizados

---

## Conclusión

Los 529 warnings no impiden que las pruebas funcionen correctamente (775 tests pasando ✅). Sin embargo, es importante abordarlos para:

1. **Mantener el código actualizado** con las últimas APIs de Python
2. **Prevenir problemas futuros** cuando las APIs deprecadas sean removidas
3. **Mejorar la calidad del código** y reducir ruido en los logs
4. **Facilitar el mantenimiento** con código más limpio

La mayoría de los warnings son de **deprecación** y se pueden corregir fácilmente con cambios menores en el código.

---

**Generado automáticamente después de ejecutar:** `pytest tests/ -n 16`














