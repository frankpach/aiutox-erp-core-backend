# Nota sobre Starlette y FastAPI

## Situación Actual

El proyecto usa **FastAPI 0.125.0**, que depende de **Starlette 0.50.0**.

## ¿Por qué no se puede reemplazar Starlette?

**FastAPI está construido sobre Starlette** - no es una dependencia opcional, es la base del framework:

- FastAPI es esencialmente una capa sobre Starlette que agrega validación con Pydantic
- Todo el código del proyecto (32+ archivos) usa FastAPI directamente
- Reemplazar Starlette requeriría reescribir todo el backend con otro framework

## ¿Es Starlette inseguro o desactualizado?

**No.** Starlette es:
- ✅ **Activamente mantenido** - última versión: 0.50.0 (Nov 2025)
- ✅ **Framework moderno** - ASGI, async/await nativo
- ✅ **Usado por FastAPI** - uno de los frameworks más populares de Python
- ✅ **Seguro** - vulnerabilidades conocidas fueron corregidas en versiones recientes

## Warnings de Deprecación

Los warnings que aparecen son **menores** y se resolverán en futuras versiones:
- `HTTP_422_UNPROCESSABLE_ENTITY` → Se actualizará a `HTTP_422_UNPROCESSABLE_CONTENT` en Starlette
- `PytestCollectionWarning` → pytest intenta recopilar métodos de Starlette como tests (no es un problema real)

## Alternativas (No Recomendadas)

Si realmente quisieras cambiar de framework, las opciones serían:

1. **Quart** - Similar a Flask pero async
   - ❌ Menos popular que FastAPI
   - ❌ Requeriría reescribir todo el código
   - ❌ Menos documentación y comunidad

2. **Litestar** - Framework moderno
   - ❌ Más nuevo, menos maduro
   - ❌ Requeriría reescribir todo el código
   - ❌ Menos ecosistema

3. **Django** - Framework tradicional
   - ❌ No es async-first
   - ❌ Requeriría reescribir todo el código
   - ❌ Más pesado

## Recomendación

**Mantener FastAPI/Starlette** porque:
1. ✅ Es el framework más moderno y popular para Python
2. ✅ Excelente documentación y comunidad
3. ✅ Los warnings son menores y se resolverán
4. ✅ Cambiar requeriría meses de trabajo reescribiendo código
5. ✅ FastAPI está actualizado (0.125.0) y Starlette también (0.50.0)

## Acciones Tomadas

1. ✅ **Actualizado FastAPI** a 0.125.0 (última versión)
2. ✅ **Eliminados filtros de warnings** - ahora verás todos los warnings reales
3. ✅ **Corregido código propio** - `datetime.utcnow()`, `asyncio.get_event_loop()`, etc.

Los warnings que aparezcan ahora son de librerías externas y se resolverán cuando Starlette/FastAPI actualicen.














