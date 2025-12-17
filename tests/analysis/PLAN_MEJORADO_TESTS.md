# Plan Mejorado para Completar y Verificar Todas las Pruebas

**Fecha de Inicio:** [Se completará al iniciar]
**Última Actualización:** [Se actualizará después de cada test]
**Estado:** 🔄 En Progreso

---

## 📋 Índice

1. [Flujo de Trabajo Completo](#flujo-de-trabajo-completo)
2. [Inicialización](#inicialización)
3. [Estado Actual](#estado-actual)
4. [Plan de Ejecución por Módulo](#plan-de-ejecución-por-módulo)
5. [Seguimiento de Progreso](#seguimiento-de-progreso)
6. [Lista de Errores y Correcciones](#lista-de-errores-y-correcciones)
7. [Manejo de Tests Saltados](#manejo-de-tests-saltados)
8. [Manejo de Warnings](#manejo-de-warnings)
9. [Procedimiento para Retomar](#procedimiento-para-retomar)
10. [Verificación Final](#verificación-final)
11. [Detección de Ciclos Infinitos](#detección-de-ciclos-infinitos)
12. [Procedimiento de Actualización del Documento](#procedimiento-de-actualización-del-documento)
13. [Comandos Útiles](#comandos-útiles)
14. [Archivos Clave](#archivos-clave)
15. [Criterios de Éxito Final](#criterios-de-éxito-final)
16. [Notas Importantes](#notas-importantes)
17. [Inicio Rápido](#inicio-rápido)

---

## 🔄 Flujo de Trabajo Completo

### Resumen del Procedimiento

1. **Inicialización:**
   - Crear archivo `last_test_{datetime}.md`
   - Configurar pytest para mejor retroalimentación
   - Ejecutar suite completa para obtener estado inicial

2. **Por Cada Módulo:**
   - Ejecutar tests del módulo
   - Capturar resultados y errores
   - Actualizar documento de seguimiento
   - Si hay errores: corregirlos inmediatamente
   - Re-ejecutar test para verificar corrección
   - Detectar ciclos infinitos (si aplica)

3. **Después de Cada Corrección:**
   - Actualizar documento marcando error como corregido
   - Documentar solución aplicada
   - Verificar que no se crearon nuevos errores

4. **Al Finalizar Todos los Módulos:**
   - Ejecutar suite completa de tests
   - Verificar cobertura
   - Generar reporte final
   - Actualizar documentación si es necesario
   - Actualizar reglas si es necesario

### Flujo Visual

```
INICIO
  ↓
Crear last_test_{datetime}.md
  ↓
Ejecutar suite completa (estado inicial)
  ↓
┌─────────────────────────────────┐
│ Por cada módulo en el plan:     │
│ 1. Ejecutar test del módulo     │
│ 2. Actualizar documento          │
│ 3. ¿Hay errores?                 │
│    SÍ → Corregir inmediatamente  │
│    NO → Siguiente módulo         │
│ 4. ¿Ciclo detectado?            │
│    SÍ → Solución de fondo       │
│    NO → Continuar               │
└─────────────────────────────────┘
  ↓
Ejecutar suite completa (verificación final)
  ↓
Generar reporte final
  ↓
FIN
```

---

## 🚀 Inicialización

### Paso 1: Crear Archivo de Seguimiento

**Al iniciar la batería de tests, crear archivo:**
```
backend/tests/analysis/last_test_{datetime}.md
```

**Formato del nombre:** `last_test_YYYYMMDD_HHMMSS.md` (ejemplo: `last_test_20250113_143022.md`)

**Comando para crear archivo:**
```bash
cd backend
uv run python tests/scripts/create_test_tracking.py
```

**O manualmente:**
```bash
cd backend/tests/analysis
# El script creará automáticamente el archivo con timestamp
python ../../tests/scripts/create_test_tracking.py
```

**Contenido inicial del archivo:**
- Estado inicial de tests
- Plan completo de ejecución
- Lista de módulos a verificar
- Estructura para seguimiento de errores
- Historial de actualizaciones

### Paso 2: Configuración de pytest para Retroalimentación

**Mejoras para tests largos sin retroalimentación:**

1. **Agregar plugins de pytest para progreso:**
   ```bash
   # Agregar a pyproject.toml en [project.optional-dependencies] dev:
   "pytest-progress>=1.0.0",
   "pytest-timeout>=2.1.0",
   ```

2. **Actualizar configuración de pytest en `pyproject.toml`:**
   ```toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   python_files = ["test_*.py", "*_test.py"]
   python_classes = ["Test*"]
   python_functions = ["test_*"]
   addopts = "-v --tb=short --durations=10 --timeout=300"
   asyncio_mode = "auto"
   timeout = 300  # 5 minutos por test
   ```

3. **Comando mejorado para ejecución con retroalimentación:**
   ```bash
   cd backend
   uv run --extra dev pytest -v --tb=short --durations=10 --timeout=300 --progress
   ```

---

## 📊 Estado Actual

### Resumen Ejecutivo

- **Tests pasando:** ~688 (89.1%) - [Se actualizará después de cada ejecución]
- **Tests fallando:** ~84 (10.9%) - [Se actualizará después de cada ejecución]
- **Tests saltados:** ~2 (0.3%) - [Se investigará y documentará cada uno]
- **Warnings:** ~[N] - [Se capturarán y clasificarán todos]
  - 🔴 Críticas: ~[N]
  - 🟡 Altas: ~[N]
  - 🟢 Medias: ~[N]
  - ⚪ Bajas: ~[N]
- **Errores:** ~1

### Mejoras Ya Implementadas

✅ **Helper de permisos:** `backend/tests/helpers.py` - `create_user_with_permission()`
✅ **Event helpers:** `backend/app/core/pubsub/event_helpers.py` - `safe_publish_event()`
✅ **Corrección de formato:** `error_code` → `code` en 18 archivos
✅ **StandardListResponse:** Corregido en 6 archivos de endpoints
✅ **11 módulos agregados a MODULE_ROLES**

---

## 📦 Plan de Ejecución por Módulo

### Orden de Ejecución (Prioridad)

**Fase 1: Módulos Core/Infraestructura (Objetivo: >90% cobertura)**
1. ✅ **auth** - `test_auth_*.py` (login, me, endpoints, service)
2. ⚠️ **users** - `test_user_management.py`
3. ⚠️ **config** - `test_config.py`
4. ⚠️ **pubsub** - `test_pubsub_*.py` (unit, integration, api)
5. ⚠️ **notifications** - `test_notifications_api.py`
6. ⚠️ **reporting** - `test_reporting_api.py`

**Fase 2: Módulos de Negocio Críticos (Objetivo: >80% cobertura)**
7. ⚠️ **products** - `test_products.py`, `test_products_events.py`
8. ✅ **tags** - `test_tags_api.py` (8 tests)
9. ✅ **tasks** - `test_tasks_api.py` (7 tests)
10. ✅ **files** - `test_files_api.py` (6 tests)
11. ✅ **activities** - `test_activities_api.py` (6 tests)
12. ✅ **workflows** - `test_workflows_api.py` (7 tests)
13. ✅ **integrations** - `test_integrations_api.py` (11 tests)
14. ✅ **preferences** - `test_preferences_api.py` (7 tests)

**Fase 3: Módulos de Negocio Secundarios (Objetivo: >80% cobertura)**
15. ⚠️ **calendar** - `test_calendar_api.py`, `test_calendar_integration.py`
16. ⚠️ **comments** - `test_comments_api.py`, `test_comments_integration.py`
17. ⚠️ **approvals** - `test_approvals_api.py`, `test_approvals_integration.py`
18. ⚠️ **templates** - `test_templates_api.py`, `test_templates_integration.py`
19. ⚠️ **import_export** - `test_import_export_api.py`, `test_import_export_integration.py`
20. ⚠️ **views** - `test_views_api.py`, `test_views_integration.py`
21. ⚠️ **automation** - `test_automation_api.py`, `test_automation_engine.py`
22. ⚠️ **search** - `test_search_api.py`

**Fase 4: Tests de Infraestructura y Seguridad**
23. ⚠️ **rbac** - `test_rbac.py`
24. ⚠️ **security** - `test_security_multi_tenant.py`
25. ⚠️ **audit** - `test_audit_logs.py`
26. ⚠️ **error_handling** - `test_error_handling.py`
27. ⚠️ **standard_responses** - `test_standard_responses.py`

**Fase 5: Tests Unitarios**
28. ⚠️ **unit/** - Todos los tests unitarios
29. ⚠️ **cli/** - Tests del CLI

---

## 📈 Seguimiento de Progreso

### Estructura de Seguimiento por Módulo

Para cada módulo, registrar:

```markdown
### Módulo: [nombre]

**Archivo de test:** `tests/integration/test_[nombre]_api.py`
**Estado:** ⏳ Pendiente | 🔄 En Progreso | ✅ Completado | ❌ Error
**Última ejecución:** [timestamp]
**Resultado:**
- Tests totales: [N]
- Tests pasando: [N]
- Tests fallando: [N]
- Tests saltados: [N]
- **Warnings:** [N] ⚠️
  - 🔴 Críticas: [N]
  - 🟡 Altas: [N]
  - 🟢 Medias: [N]
  - ⚪ Bajas: [N]
- Tiempo de ejecución: [X]s

**Errores encontrados:**
1. [Descripción del error] - Estado: ⏳ Pendiente | ✅ Corregido
2. [Descripción del error] - Estado: ⏳ Pendiente | ✅ Corregido

**Tests saltados:**
1. `test_nombre` - Razón: [Razón] - Tipo: ✅ Intencional | ❌ Problema - Acción: [Mantener | Corregir]

**Warnings encontrados:**
1. [Warning crítico] - Severidad: 🔴 - Estado: ⏳ Pendiente | ✅ Corregido | 📝 Aceptado (razón: [razón])
2. [Warning alta] - Severidad: 🟡 - Estado: ⏳ Pendiente | ✅ Corregido | 📝 Aceptado (razón: [razón])

**Acciones realizadas:**
- [Timestamp] - [Acción realizada]
- [Timestamp] - [Acción realizada]
- [Timestamp] - Investigado test saltado: [nombre]
- [Timestamp] - Clasificado warning: [descripción]

**Próximas acciones:**
- [ ] [Acción pendiente]
```

---

## 🐛 Lista de Errores y Correcciones

### Categorías de Errores

#### 1. Errores de Permisos (403 Forbidden)
**Patrón:** Tests que fallan con `assert 403 == 201` o `assert 403 == 200`

**Solución estándar:**
```python
# ANTES
def test_example(client, test_user, auth_headers, db_session):
    response = client.post("/api/v1/endpoint", json=data, headers=auth_headers)

# DESPUÉS
def test_example(client, test_user, db_session):
    headers = create_user_with_permission(db_session, test_user, "module_name", "manager")
    response = client.post("/api/v1/endpoint", json=data, headers=headers)
```

**Lista de errores:**
- [ ] `test_create_tag` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_create_task` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_upload_file` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_get_report` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_create_report` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_save_view` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_create_dashboard` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_index_entity` - 403 Forbidden - ⏳ Pendiente
- [ ] `test_get_suggestions` - 403 Forbidden - ⏳ Pendiente

#### 2. Errores de Formato de Respuesta
**Patrón:** `AssertionError` relacionado con estructura de respuesta

**Solución estándar:**
- Verificar que endpoints usen `StandardResponse` o `StandardListResponse`
- Eliminar `success=True` de respuestas
- Verificar que errores usen `code` en lugar de `error_code`

**Lista de errores:**
- [ ] `test_login_success` - Formato de respuesta - ⏳ Pendiente
- [ ] `test_list_roles_returns_standard_list_response` - Formato - ⏳ Pendiente

#### 3. Errores de Event Loop PubSub
**Patrón:** "There is no current event loop" o "Failed to publish [event].created event"

**Solución estándar:**
```python
# Usar safe_publish_event en lugar de publish_event directamente
from app.core.pubsub.event_helpers import safe_publish_event

safe_publish_event("module.entity.created", {"entity_id": entity.id})
```

**Lista de errores:**
- [ ] Activities - Event loop - ⏳ Pendiente
- [ ] Tasks - Event loop - ⏳ Pendiente
- [ ] Calendar - Event loop - ⏳ Pendiente
- [ ] Comments - Event loop - ⏳ Pendiente
- [ ] Templates - Event loop - ⏳ Pendiente
- [ ] Import/Export - Event loop - ⏳ Pendiente
- [ ] Products - Event loop - ⏳ Pendiente

#### 4. Errores de Base de Datos
**Patrón:** `sqlalchemy.exc.ProgrammingError`, `sqlalchemy.exc.InternalError`, `psycopg2.errors.InFailedSqlTransaction`

**Solución estándar:**
- Verificar cleanup de transacciones
- Asegurar que `db_session.refresh()` se llame después de commits
- Verificar que no haya transacciones abiertas

**Lista de errores:**
- [ ] Tags - DB transaction - ⏳ Pendiente
- [ ] Tasks - DB transaction - ⏳ Pendiente
- [ ] Workflows - DB transaction - ⏳ Pendiente
- [ ] Files - DB transaction - ⏳ Pendiente
- [ ] Integrations - DB transaction - ⏳ Pendiente

#### 5. Errores de Validación/Esquemas
**Patrón:** `AttributeError`, `TypeError: 'NoneType' object`, validación de schemas fallida

**Solución estándar:**
- Verificar que servicios tengan los métodos necesarios
- Verificar que objetos no sean None antes de usar
- Revisar validaciones de schemas

**Lista de errores:**
- [ ] Tags - Validación - ⏳ Pendiente
- [ ] Tasks - Validación - ⏳ Pendiente
- [ ] Notifications - Validación - ⏳ Pendiente
- [ ] Templates - Validación - ⏳ Pendiente

---

## ⏭️ Manejo de Tests Saltados

### Procedimiento Obligatorio para Tests Saltados

**IMPORTANTE:** Todos los tests saltados deben ser investigados y documentados. No se puede dejar ningún test saltado sin justificación explícita.

### Paso 1: Identificar Tests Saltados

Después de cada ejecución de tests, identificar todos los tests marcados como `SKIPPED`:

```bash
# Capturar tests saltados
uv run --extra dev pytest -v --tb=no | grep -i "skipped"
```

### Paso 2: Investigar la Razón del Skip

Para cada test saltado, determinar la razón:

1. **Revisar el código del test:**
   ```python
   @pytest.mark.skip(reason="...")  # Razón explícita
   @pytest.mark.skipif(condition, reason="...")  # Condición
   ```

2. **Verificar si es intencional:**
   - ¿El test está marcado con `@pytest.mark.skip` con una razón clara?
   - ¿Es un test que requiere condiciones específicas (ej: Redis, servicios externos)?
   - ¿Es un test temporalmente deshabilitado?

3. **Verificar si es un problema:**
   - ¿El test falla y fue saltado para ocultar el error?
   - ¿Falta alguna dependencia o configuración?
   - ¿Hay un problema de infraestructura?

### Paso 3: Documentar en `last_test_{datetime}.md`

**Para cada test saltado, agregar entrada en el archivo de seguimiento:**

```markdown
### Tests Saltados - Módulo: [nombre]

#### Test: `test_nombre_del_test`
- **Archivo:** `tests/integration/test_[module]_api.py::test_nombre_del_test`
- **Razón del skip:** [Razón encontrada]
- **Tipo:**
  - ✅ Intencional (requiere condición específica)
  - ❌ Problema (debe corregirse)
- **Acción requerida:**
  - [ ] Mantener saltado (si es intencional)
  - [ ] Corregir y habilitar (si es problema)
- **Justificación:** [Explicación detallada]
- **Fecha de revisión:** [YYYY-MM-DD HH:MM:SS]
```

### Paso 4: Decidir Acción

**Si es INTENCIONAL:**
- ✅ Documentar razón clara en el código del test
- ✅ Asegurar que el `reason` del `@pytest.mark.skip` sea descriptivo
- ✅ Verificar que la condición sea válida (ej: `@pytest.mark.skipif(not redis_available, reason="Requires Redis")`)
- ✅ Mantener el test saltado
- ✅ Documentar en `last_test_{datetime}.md` como intencional

**Si es un PROBLEMA:**
- ❌ NO dejar el test saltado sin corregir
- ❌ Investigar y corregir la causa raíz
- ❌ Habilitar el test después de la corrección
- ❌ Verificar que el test pase
- ❌ Documentar la corrección en `last_test_{datetime}.md`

### Paso 5: Actualizar Código del Test

**Para tests intencionales, asegurar que tengan razón clara:**

```python
# ✅ CORRECTO - Razón clara
@pytest.mark.skipif(
    not redis_available,
    reason="Test requires Redis connection. Run with Redis available."
)

# ✅ CORRECTO - Test temporalmente deshabilitado con razón
@pytest.mark.skip(
    reason="Temporarily disabled due to external API changes. TODO: Update test after API migration."
)

# ❌ INCORRECTO - Sin razón
@pytest.mark.skip()

# ❌ INCORRECTO - Razón vaga
@pytest.mark.skip(reason="Doesn't work")
```

### Criterios de Éxito para Tests Saltados

- ✅ Todos los tests saltados tienen razón documentada
- ✅ Todos los tests saltados están clasificados (intencional vs problema)
- ✅ Todos los tests saltados están documentados en `last_test_{datetime}.md`
- ✅ Tests saltados por problemas han sido corregidos o están en proceso
- ✅ El informe final incluye sección explícita sobre tests saltados

### Ejemplo de Documentación en `last_test_{datetime}.md`

```markdown
## 📊 Resumen de Tests Saltados

**Total de tests saltados:** [N]
**Tests intencionales:** [N]
**Tests con problemas:** [N]

### Detalle por Módulo

#### Módulo: auth
- `test_redis_rate_limiting` - ✅ Intencional - Requiere Redis
- `test_external_api_integration` - ❌ Problema - API externa no disponible

#### Módulo: products
- `test_import_large_file` - ✅ Intencional - Requiere archivo de prueba grande

### Acciones Pendientes
- [ ] Corregir `test_external_api_integration` en módulo auth
- [ ] Verificar que todos los tests intencionales tienen razón clara
```

---

## ⚠️ Manejo de Warnings

### Procedimiento Obligatorio para Warnings

**IMPORTANTE:** Todos los warnings deben ser capturados, clasificados y documentados. Warnings de alta severidad requieren acción inmediata.

### Paso 1: Capturar Warnings

**Configurar pytest para capturar warnings:**

```bash
# Ejecutar tests con captura de warnings
uv run --extra dev pytest -v --tb=short -W default::Warning
```

**O con configuración en `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
filterwarnings = [
    "error",  # Convertir warnings críticos en errores
    "ignore::DeprecationWarning:app",  # Ignorar warnings específicos solo si es necesario
    "default",  # Mostrar todos los demás warnings
]
```

### Paso 2: Clasificar Warnings por Severidad

**Categorías de severidad:**

#### 🔴 **CRÍTICA** (Requiere acción inmediata)
- Warnings de seguridad (ej: uso de funciones inseguras)
- Warnings de deprecación en código crítico
- Warnings de configuración incorrecta
- Warnings que pueden causar errores en producción

#### 🟡 **ALTA** (Requiere acción en corto plazo)
- Warnings de deprecación en código activo
- Warnings de rendimiento
- Warnings de compatibilidad futura
- Warnings de buenas prácticas

#### 🟢 **MEDIA** (Recomendado corregir)
- Warnings de estilo de código
- Warnings informativos
- Warnings de optimización menor

#### ⚪ **BAJA** (Opcional)
- Warnings cosméticos
- Warnings de librerías externas (no controlables)
- Warnings informativos sin impacto

### Paso 3: Registrar en `last_test_{datetime}.md`

**Para cada warning, agregar entrada:**

```markdown
### Warnings - Módulo: [nombre]

#### Warning: [Descripción]
- **Tipo:** [DeprecationWarning, PendingDeprecationWarning, UserWarning, etc.]
- **Severidad:** 🔴 Crítica | 🟡 Alta | 🟢 Media | ⚪ Baja
- **Ubicación:** `app/module/file.py:line`
- **Mensaje completo:** [Mensaje del warning]
- **Acción requerida:**
  - [ ] Corregir inmediatamente (si es crítica)
  - [ ] Planificar corrección (si es alta/media)
  - [ ] Documentar como aceptable (si es baja)
- **Fecha de detección:** [YYYY-MM-DD HH:MM:SS]
- **Estado:** ⏳ Pendiente | 🔄 En Progreso | ✅ Corregido | 📝 Aceptado
```

### Paso 4: Definir Cuándo un Warning Requiere Acción

**Warnings que SIEMPRE requieren acción:**

1. **Warnings de seguridad:**
   - Uso de funciones inseguras
   - Configuraciones de seguridad incorrectas
   - Exposición de información sensible

2. **Warnings de deprecación en código crítico:**
   - Funciones que se eliminarán en próxima versión
   - APIs que cambiarán y afectan funcionalidad core

3. **Warnings de configuración:**
   - Variables de entorno faltantes
   - Configuraciones incorrectas que pueden causar errores

**Warnings que pueden documentarse como aceptables:**

1. **Warnings de librerías externas:**
   - Warnings de dependencias de terceros que no controlamos
   - Warnings conocidos sin solución disponible

2. **Warnings informativos:**
   - Warnings que no afectan funcionalidad
   - Warnings cosméticos

### Paso 5: Incluir en Seguimiento de Progreso

**Actualizar sección de seguimiento por módulo:**

```markdown
### Módulo: [nombre]

**Resultado:**
- Tests totales: [N]
- Tests pasando: [N] ✅
- Tests fallando: [N] ❌
- Tests saltados: [N] ⏭️
- **Warnings:** [N] ⚠️
  - 🔴 Críticas: [N]
  - 🟡 Altas: [N]
  - 🟢 Medias: [N]
  - ⚪ Bajas: [N]
- Tiempo de ejecución: [X]s

**Warnings encontrados:**
1. [Warning crítico] - Estado: ⏳ Pendiente | ✅ Corregido
2. [Warning alta] - Estado: ⏳ Pendiente | ✅ Corregido
```

### Criterios de Éxito para Warnings

- ✅ Todos los warnings están capturados y registrados
- ✅ Todos los warnings están clasificados por severidad
- ✅ Warnings críticas han sido corregidas o están en proceso
- ✅ Warnings altas tienen plan de corrección documentado
- ✅ El informe final incluye sección explícita sobre warnings
- ✅ Si no se hizo nada con un warning, la razón está explícitamente documentada

### Ejemplo de Documentación en `last_test_{datetime}.md`

```markdown
## ⚠️ Resumen de Warnings

**Total de warnings:** [N]
**Warnings críticas:** [N] 🔴
**Warnings altas:** [N] 🟡
**Warnings medias:** [N] 🟢
**Warnings bajas:** [N] ⚪

### Warnings Críticas (Acción Requerida)

1. **DeprecationWarning en `app/core/auth/jwt.py:45`**
   - **Mensaje:** `jwt.encode()` is deprecated, use `jwt.encode_unsafe()` instead
   - **Acción:** Actualizar a nueva API de JWT
   - **Estado:** 🔄 En Progreso
   - **Fecha límite:** [YYYY-MM-DD]

### Warnings Aceptadas (Con Justificación)

1. **UserWarning en `app/core/integrations/external_api.py:120`**
   - **Mensaje:** External API library shows warning about rate limits
   - **Razón de aceptación:** Warning de librería externa, no controlable. Ya manejamos rate limiting en nuestro código.
   - **Estado:** 📝 Aceptado
   - **Fecha de revisión:** [YYYY-MM-DD]
```

---

## 🔄 Procedimiento para Retomar

### Si el Proceso se Interrumpe

1. **Leer el archivo `last_test_{datetime}.md` más reciente:**
   ```bash
   ls -lt backend/tests/analysis/last_test_*.md | head -1
   ```

2. **Identificar el último módulo procesado:**
   - Buscar en el documento la sección "Seguimiento de Progreso"
   - Encontrar el último módulo con estado "✅ Completado" o "🔄 En Progreso"

3. **Continuar desde el siguiente módulo:**
   - Ejecutar el módulo siguiente en el orden establecido
   - Actualizar el documento con los resultados

4. **Verificar errores pendientes:**
   - Revisar la sección "Lista de Errores y Correcciones"
   - Continuar corrigiendo errores pendientes

### Comando para Retomar

```bash
# 1. Leer el último archivo de seguimiento
cat backend/tests/analysis/last_test_*.md | head -50

# 2. Continuar desde el módulo siguiente
# [Ejecutar el módulo siguiente según el plan]
```

---

## ✅ Verificación Final

### Antes de Dar por Terminado

**Paso 1: Ejecutar Suite Completa de Tests**
```bash
cd backend
uv run --extra dev pytest -v --tb=short --durations=10 --timeout=300 -W default::Warning
```

**Paso 2: Verificar Cobertura**
```bash
uv run --extra dev pytest --cov=app --cov-report=html --cov-report=term-missing
```

**Paso 3: Verificar Criterios de Éxito**
- [ ] Todos los tests pasan (0 fallos)
- [ ] Cobertura >90% para módulos core (auth, permissions, multi-tenancy)
- [ ] Cobertura >80% para módulos de negocio
- [ ] Todos los endpoints API tienen tests de integración
- [ ] Todos los servicios críticos tienen tests unitarios
- [ ] Tests validan formato de respuestas según API contract
- [ ] Tests incluyen casos edge y validaciones de seguridad
- [ ] **Todos los tests saltados están documentados y justificados**
- [ ] **Tests saltados por problemas han sido corregidos**
- [ ] **Todos los warnings están capturados y clasificados**
- [ ] **Warnings críticas han sido corregidas o tienen plan documentado**
- [ ] **Si no se hizo nada con un warning/test saltado, la razón está explícitamente documentada**

**Paso 4: Generar Reporte Final**
```bash
# Crear reporte final
cat > backend/tests/analysis/test_verification_report.md << EOF
# Reporte Final de Verificación de Tests

**Fecha:** $(date +%Y-%m-%d\ %H:%M:%S)
**Estado:** ✅ Completado

## Resumen
- Tests totales: [N]
- Tests pasando: [N]
- Tests fallando: [N]
- **Tests saltados: [N]**
  - Tests intencionales: [N]
  - Tests con problemas: [N]
- **Warnings: [N]**
  - 🔴 Críticas: [N]
  - 🟡 Altas: [N]
  - 🟢 Medias: [N]
  - ⚪ Bajas: [N]
- Cobertura general: [X]%
- Cobertura core: [X]%
- Cobertura negocio: [X]%

## Módulos Verificados
[Lista de módulos con estado]

## Tests Saltados

### Resumen
- **Total:** [N]
- **Intencionales:** [N] (documentados y justificados)
- **Con problemas:** [N] (corregidos o en proceso)

### Detalle
[Lista detallada de cada test saltado con razón y acción tomada]

### Acciones Realizadas
- [ ] Todos los tests saltados investigados
- [ ] Todos los tests saltados documentados en `last_test_{datetime}.md`
- [ ] Tests saltados por problemas corregidos o tienen plan de corrección
- [ ] Tests intencionales tienen razón clara en código

### Justificación de Tests Saltados Sin Acción
**Si algún test saltado no fue corregido, explicar explícitamente la razón:**
- Test: `test_nombre`
- Razón del skip: [Razón]
- Por qué no se corrigió: [Explicación detallada]
- Plan futuro: [Si aplica]

## Warnings

### Resumen
- **Total:** [N]
- **Críticas:** [N] (corregidas: [N], pendientes: [N])
- **Altas:** [N] (corregidas: [N], pendientes: [N])
- **Medias:** [N] (corregidas: [N], aceptadas: [N])
- **Bajas:** [N] (aceptadas: [N])

### Detalle
[Lista detallada de warnings con severidad y acción tomada]

### Acciones Realizadas
- [ ] Todos los warnings capturados y registrados
- [ ] Todos los warnings clasificados por severidad
- [ ] Warnings críticas corregidas o tienen plan documentado
- [ ] Warnings documentadas en `last_test_{datetime}.md`

### Justificación de Warnings Sin Acción
**Si algún warning no fue corregido, explicar explícitamente la razón:**
- Warning: [Descripción]
- Severidad: [Crítica/Alta/Media/Baja]
- Por qué no se corrigió: [Explicación detallada]
- Impacto de no corregir: [Análisis de impacto]
- Plan futuro: [Si aplica]

## Recomendaciones
[Recomendaciones finales]
EOF
```

---

## 🔁 Detección de Ciclos Infinitos

### Procedimiento para Detectar y Resolver Ciclos

**Definición de Ciclo Infinito:**
- Mismo error aparece 3+ veces después de intentos de corrección
- Corrección aplicada pero error persiste o cambia a otro error relacionado
- Múltiples correcciones en el mismo archivo sin resolver el problema
- Mismo patrón de error-cambio-error se repite

**Procedimiento de Detección:**

1. **Registrar intentos de corrección en el documento:**
   ```markdown
   ### Error: [Descripción]
   - Intento 1: [Timestamp] - [Acción] - ❌ Falló
   - Intento 2: [Timestamp] - [Acción] - ❌ Falló
   - Intento 3: [Timestamp] - [Acción] - ❌ Falló
   - **DECISIÓN:** 🔴 Ciclo detectado - Pasar a solución de fondo
   ```

2. **Cuando se detecta un ciclo (después de 3 intentos):**
   - **DETENER** correcciones iterativas inmediatamente
   - **MARCAR** error como 🔴 Ciclo detectado en el documento
   - **ANALIZAR** la causa raíz del problema (no solo síntomas)
   - **DISEÑAR** solución de fondo (no parches)
   - **DOCUMENTAR** análisis y solución de fondo en el archivo de seguimiento
   - **IMPLEMENTAR** solución de fondo
   - **VERIFICAR** que la solución resuelve el problema completamente
   - **ACTUALIZAR** documento marcando ciclo como resuelto

**Indicadores de Ciclo:**
- ✅ Error aparece 3+ veces con misma descripción
- ✅ Múltiples archivos modificados para "corregir" el mismo error
- ✅ Error cambia de forma pero persiste (ej: 403 → 500 → 403)
- ✅ Correcciones aplicadas pero tests siguen fallando
- ✅ Mismo patrón en múltiples módulos

**Ejemplo de Solución de Fondo:**

```markdown
### 🔴 Ciclo Detectado: Error de Permisos en Múltiples Tests

**Problema:** Múltiples tests fallan con 403 después de aplicar create_user_with_permission

**Historial de Intentos:**
- Intento 1: [2025-01-13 10:00:00] - Agregar ModuleRole manualmente - ❌ Falló
- Intento 2: [2025-01-13 10:15:00] - Usar create_user_with_permission - ❌ Falló
- Intento 3: [2025-01-13 10:30:00] - Refrescar usuario después de commit - ❌ Falló
- **DECISIÓN:** 🔴 Ciclo detectado - Pasar a solución de fondo

**Análisis de Causa Raíz:**
1. El helper create_user_with_permission no está refrescando correctamente los permisos
2. El token generado no incluye los nuevos permisos porque el usuario no se refresca
3. La caché de permisos en el servicio de auth no se está limpiando
4. El token JWT se genera antes de que los permisos estén disponibles

**Solución de Fondo:**
1. Modificar `create_user_with_permission` en `backend/tests/helpers.py`:
   - Forzar refresh completo del usuario desde DB
   - Limpiar caché de permisos antes de generar token
   - Verificar que permisos estén en el usuario antes de crear token

2. Modificar `AuthService.create_access_token_for_user`:
   - Asegurar que siempre lea permisos frescos de DB
   - No usar caché de permisos para tokens de test

3. Agregar fixture para limpiar caché de permisos antes de cada test

**Implementación:**
[Detalles específicos de código modificado]

**Archivos Modificados:**
- `backend/tests/helpers.py` - Línea X: [Cambio]
- `backend/app/services/auth_service.py` - Línea Y: [Cambio]
- `backend/tests/conftest.py` - Línea Z: [Cambio]

**Verificación:**
- [x] Tests pasan después de la solución
- [x] No se detectan más ciclos relacionados
- [x] Solución aplicada a todos los módulos afectados
```

**Regla de Oro:**
> Si después de 3 intentos el error persiste, **DETENER** y pasar a solución de fondo.
> No continuar con correcciones iterativas que no resuelven el problema raíz.

---

## 📝 Procedimiento de Actualización del Documento

### Después de Cada Test de Módulo

**Paso 1: Ejecutar Test del Módulo**
```bash
cd backend
uv run --extra dev pytest tests/integration/test_[module]_api.py -v --tb=short --durations=10 --timeout=300 -W default::Warning
```

**Paso 2: Capturar Resultados**
- Copiar salida completa del comando
- Extraer estadísticas (passed, failed, skipped)
- Capturar warnings (usar `-W default::Warning`)
- Identificar errores específicos
- Identificar tests saltados
- Clasificar warnings por severidad

**Paso 3: Actualizar Archivo de Seguimiento**

**Ubicación:** `backend/tests/analysis/last_test_{datetime}.md`

**Opción A: Usar Script Automático (Recomendado)**
```bash
cd backend
# Ejecutar test y capturar salida (incluyendo warnings)
uv run --extra dev pytest tests/integration/test_[module]_api.py -v --tb=short -W default::Warning > test_output.txt 2>&1

# Actualizar archivo de seguimiento
uv run python tests/scripts/update_test_tracking.py \
  --module "[module_name]" \
  --test-file "tests/integration/test_[module]_api.py" \
  --output "$(cat test_output.txt)" \
  --errors "Error 1" "Error 2" \
  --actions "Ejecutado test" "Aplicada corrección X"
```

**Opción B: Actualización Manual**

**Actualizar secciones:**

1. **Actualizar "Seguimiento de Progreso por Módulo":**
   ```markdown
   ### Módulo: [nombre]

   **Archivo de test:** `tests/integration/test_[nombre]_api.py`
   **Estado:** ✅ Completado
   **Última ejecución:** [YYYY-MM-DD HH:MM:SS]
   **Resultado:**
   - Tests totales: [N]
   - Tests pasando: [N] ✅
   - Tests fallando: [N] ❌
   - Tests saltados: [N] ⏭️
   - **Warnings:** [N] ⚠️
     - 🔴 Críticas: [N]
     - 🟡 Altas: [N]
     - 🟢 Medias: [N]
     - ⚪ Bajas: [N]
   - Tiempo de ejecución: [X]s

   **Errores encontrados:**
   1. [Descripción del error] - Estado: ⏳ Pendiente
   2. [Descripción del error] - Estado: ⏳ Pendiente

   **Tests saltados:**
   1. `test_nombre` - Razón: [Razón] - Tipo: ✅ Intencional | ❌ Problema
   - Acción: [Mantener | Corregir]

   **Warnings encontrados:**
   1. [Warning crítico] - Severidad: 🔴 - Estado: ⏳ Pendiente | ✅ Corregido
   2. [Warning alta] - Severidad: 🟡 - Estado: ⏳ Pendiente | ✅ Corregido

   **Acciones realizadas:**
   - [Timestamp] - Ejecutado test del módulo
   - [Timestamp] - [Acción de corrección si aplica]
   - [Timestamp] - Investigado test saltado: [nombre]
   - [Timestamp] - Clasificado warning: [descripción]

   **Próximas acciones:**
   - [ ] [Acción pendiente]
   ```

2. **Actualizar "Lista de Errores y Correcciones":**
   - Agregar nuevos errores encontrados
   - Actualizar estado de errores corregidos (⏳ Pendiente → ✅ Corregido)

3. **Actualizar "Historial de Actualizaciones":**
   ```markdown
   ### [YYYY-MM-DD HH:MM:SS] - Módulo: [nombre]
   - Ejecutado test del módulo [nombre]
   - Resultado: [N] pasando, [N] fallando
   - Errores encontrados: [Lista]
   - Acciones: [Acciones realizadas]
   ```

**Paso 4: Si Hay Errores, Corregirlos Inmediatamente**

1. **Analizar error:**
   - Identificar tipo de error (permisos, formato, DB, eventos, validación)
   - Buscar patrón similar en otros módulos
   - Verificar si ya existe solución conocida

2. **Aplicar corrección:**
   - Implementar solución según patrón estándar
   - Verificar que la corrección no rompa otros tests

3. **Re-ejecutar test:**
   ```bash
   uv run --extra dev pytest tests/integration/test_[module]_api.py -v
   ```

4. **Actualizar documento:**
   - Marcar error como ✅ Corregido
   - Documentar la solución aplicada
   - Actualizar estadísticas

**Paso 5: Detectar Ciclos Infinitos**

Si el mismo error persiste después de 3 intentos de corrección:
- **DETENER** correcciones iterativas inmediatamente
- Marcar como 🔴 Ciclo detectado en el documento
- Pasar a solución de fondo
- Documentar análisis de causa raíz
- Implementar solución de fondo
- Verificar que resuelve el problema
- Actualizar documento con solución de fondo

**Importante:** No continuar con más de 3 intentos de corrección iterativa.
Si después de 3 intentos el error persiste, es necesario analizar la causa raíz y diseñar una solución de fondo.

### Plantilla de Actualización

```markdown
## Actualización: [YYYY-MM-DD HH:MM:SS]

### Módulo: [nombre] - [Estado]

**Resultado de ejecución:**
```
[Salida completa del comando pytest]
```

**Resumen:**
- Tests totales: [N]
- Tests pasando: [N] ✅
- Tests fallando: [N] ❌
- Tests saltados: [N] ⏭️
- **Warnings:** [N] ⚠️ (🔴 [N] | 🟡 [N] | 🟢 [N] | ⚪ [N])
- Tiempo: [X]s

**Errores encontrados:**
1. [Error 1] - Estado: ⏳ Pendiente | ✅ Corregido | 🔴 Ciclo detectado
2. [Error 2] - Estado: ⏳ Pendiente | ✅ Corregido | 🔴 Ciclo detectado

**Tests saltados:**
1. `test_nombre` - Razón: [Razón] - Tipo: ✅ Intencional | ❌ Problema - Acción: [Mantener | Corregir]

**Warnings encontrados:**
1. [Warning crítico] - Severidad: 🔴 - Estado: ⏳ Pendiente | ✅ Corregido | 📝 Aceptado (razón: [razón])
2. [Warning alta] - Severidad: 🟡 - Estado: ⏳ Pendiente | ✅ Corregido | 📝 Aceptado (razón: [razón])

**Acciones realizadas:**
- [Timestamp] - Ejecutado test del módulo
- [Timestamp] - [Acción de corrección]
- [Timestamp] - Re-ejecutado test después de corrección
- [Timestamp] - Investigado test saltado: [nombre]
- [Timestamp] - Clasificado warning: [descripción]

**Próximas acciones:**
- [ ] [Acción siguiente]
```

---

## 🛠️ Comandos Útiles

### Ejecución de Tests

```bash
# Ejecutar todos los tests con retroalimentación (incluyendo warnings)
cd backend
uv run --extra dev pytest -v --tb=short --durations=10 --timeout=300 -W default::Warning

# Tests de un módulo específico
uv run --extra dev pytest tests/integration/test_[module]_api.py -v

# Tests con cobertura
uv run --extra dev pytest --cov=app --cov-report=html --cov-report=term

# Solo tests fallando (última ejecución)
uv run --extra dev pytest --lf -v

# Tests marcados (ej: redis)
uv run --extra dev pytest -m "redis" -v

# Tests con timeout individual
uv run --extra dev pytest --timeout=300 -v
```

### Análisis de Resultados

```bash
# Contar tests pasando/fallando/saltados y warnings
uv run --extra dev pytest --tb=no -q -W default::Warning | Select-String -Pattern "passed|failed|error|skipped|warning"

# Generar reporte JSON (incluyendo warnings)
uv run --extra dev pytest --json-report --json-report-file=test_report.json -W default::Warning

# Ver tests más lentos
uv run --extra dev pytest --durations=20

# Capturar solo warnings
uv run --extra dev pytest -W default::Warning 2>&1 | Select-String -Pattern "warning"
```

---

## 📚 Archivos Clave

- **Helper de tests:** `backend/tests/helpers.py` - `create_user_with_permission()`
- **Event helpers:** `backend/app/core/pubsub/event_helpers.py` - `safe_publish_event()`
- **Configuración:** `backend/tests/conftest.py` - Fixtures y setup
- **Reglas:** `rules/tests.md` - Estándares de testing
- **Permisos:** `backend/app/core/auth/permissions.py` - MODULE_ROLES

---

## 🎯 Criterios de Éxito Final

- ✅ Todos los tests pasan (0 fallos)
- ✅ Cobertura >90% para módulos core (auth, permissions, multi-tenancy)
- ✅ Cobertura >80% para módulos de negocio
- ✅ Todos los endpoints API tienen tests de integración
- ✅ Todos los servicios críticos tienen tests unitarios
- ✅ Tests validan formato de respuestas según API contract
- ✅ Tests incluyen casos edge y validaciones de seguridad
- ✅ **Todos los tests saltados están documentados y justificados**
- ✅ **Tests saltados por problemas han sido corregidos o tienen plan documentado**
- ✅ **Todos los warnings están capturados y clasificados por severidad**
- ✅ **Warnings críticas han sido corregidas o tienen plan de corrección documentado**
- ✅ **Si no se hizo nada con un warning/test saltado, la razón está explícitamente documentada en el informe final**
- ✅ No hay ciclos infinitos de error-cambio-error
- ✅ Documentación actualizada
- ✅ Reglas actualizadas si es necesario

---

## 📌 Notas Importantes

1. **Actualizar el documento después de CADA test ejecutado**
2. **Marcar errores como corregidos cuando se solucionen**
3. **Detectar ciclos infinitos y pasar a soluciones de fondo**
4. **Ejecutar suite completa antes de dar por terminado**
5. **Documentar todas las decisiones y cambios realizados**
6. **⚠️ OBLIGATORIO: Investigar y documentar TODOS los tests saltados**
7. **⚠️ OBLIGATORIO: Capturar, clasificar y documentar TODOS los warnings**
8. **⚠️ OBLIGATORIO: Si no se hace nada con un warning/test saltado, explicar explícitamente la razón en el informe final**

---

## 🚀 Inicio Rápido

### Comandos para Empezar

```bash
# 1. Crear archivo de seguimiento
cd backend
uv run python tests/scripts/create_test_tracking.py

# 2. Ejecutar suite completa para obtener estado inicial (incluyendo warnings)
uv run --extra dev pytest -v --tb=short --durations=10 --timeout=300 -W default::Warning > initial_test_output.txt 2>&1

# 3. Ver último archivo de seguimiento creado
ls -lt backend/tests/analysis/last_test_*.md | head -1

# 4. Continuar con el primer módulo del plan
```

### Ejemplo de Flujo por Módulo

```bash
# Ejemplo: Módulo "tags"

# 1. Ejecutar test (incluyendo warnings)
cd backend
uv run --extra dev pytest tests/integration/test_tags_api.py -v --tb=short -W default::Warning > test_tags_output.txt 2>&1

# 2. Ver resultados
cat test_tags_output.txt

# 3. Actualizar documento (manual o con script)
# Opción A: Manual - Editar last_test_*.md
# Opción B: Script (si hay errores específicos)
uv run python tests/scripts/update_test_tracking.py \
  --module "tags" \
  --test-file "tests/integration/test_tags_api.py" \
  --output "$(cat test_tags_output.txt)"

# 4. Si hay errores, corregirlos y re-ejecutar
# [Aplicar correcciones]
uv run --extra dev pytest tests/integration/test_tags_api.py -v

# 5. Continuar con siguiente módulo
```

### Comandos de Utilidad

```bash
# Ver progreso actual
cat backend/tests/analysis/last_test_*.md | grep -A 5 "Seguimiento de Progreso"

# Ver errores pendientes
cat backend/tests/analysis/last_test_*.md | grep -A 10 "Errores Pendientes"

# Ver último módulo procesado
cat backend/tests/analysis/last_test_*.md | grep "### Módulo:" | tail -1

# Contar tests pasando/fallando/saltados y warnings
uv run --extra dev pytest --tb=no -q -W default::Warning | Select-String -Pattern "passed|failed|error|skipped|warning"

---

**Última actualización:** [Se actualizará automáticamente]
