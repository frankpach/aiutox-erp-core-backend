# Cómo Iniciar el Backend con Logs Visibles

**Fecha**: 2025-01-27

## Comando Recomendado (con logs visibles)

### Opción 1: Usando `uv` (Recomendado)

```bash
cd backend

# Iniciar servidor con logs detallados
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Opción 2: Con nivel de logging explícito

```bash
cd backend

# Iniciar servidor con logs INFO (muestra mensajes [LOGIN])
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info
```

### Opción 3: Con Python directamente

```bash
cd backend

# Activar entorno virtual (si usas venv)
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Iniciar servidor
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

## Niveles de Logging

### `--log-level debug`
- Muestra TODOS los logs, incluyendo DEBUG
- Útil para debugging detallado
- Puede ser muy verboso

### `--log-level info` (Recomendado para desarrollo)
- Muestra logs INFO, WARNING, ERROR
- Incluye los mensajes `[LOGIN]` que agregamos
- Balance entre información y ruido

### `--log-level warning`
- Solo muestra WARNING y ERROR
- Menos verboso, pero puede ocultar información importante

## Verificar que los Logs Funcionan

Después de iniciar el servidor, deberías ver:

1. **Al iniciar:**
   ```
   INFO:     Started server process [xxxxx]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
   ```

2. **Al hacer login (con `--log-level info` o `debug`):**
   ```
   INFO:     [LOGIN] Creating tokens for user <user_id>, email=<email>
   DEBUG:    [LOGIN] Step 1: Creating access token for user <user_id>
   DEBUG:    [LOGIN] Step 1: Access token created successfully
   DEBUG:    [LOGIN] Step 2: Creating refresh token for user <user_id>, remember_me=False
   DEBUG:    [LOGIN] Step 2: Refresh token created successfully
   INFO:     [LOGIN] Tokens created successfully for user <user_id>
   ```

3. **Si hay un error:**
   ```
   ERROR:    [LOGIN] Error creating tokens for user <user_id>: <error_message>
   Traceback (most recent call last):
     ...
   ```

## Configuración de Logging en el Código

El código está configurado para usar `DEBUG` cuando `settings.DEBUG = True`.

**Cambios recientes (2025-01-27):**
- ✅ Se importa el módulo `app.core.logging` en `main.py` para inicializar los loggers
- ✅ El logger "app" está configurado para propagar logs al root logger
- ✅ El root logger también está configurado para mostrar logs DEBUG

Para habilitar logs DEBUG, asegúrate de que en tu `.env`:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

**Nota**: Aunque `LOG_LEVEL` esté configurado, el nivel de logging de uvicorn (`--log-level`) también afecta qué logs se muestran. Usa `--log-level debug` para ver todos los logs.

## Solución de Problemas

### No veo los logs `[LOGIN]`

**Problema**: Los mensajes DEBUG no se muestran con `--log-level info`

**Solución**: Usa `--log-level debug`:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Los logs aparecen pero sin colores/formato

**Solución**: Esto es normal. Los logs se muestran en formato texto plano en la consola.

### Quiero ver solo errores

**Solución**: Usa `--log-level warning`:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level warning
```

## Comando Completo Recomendado

Para desarrollo con todos los logs visibles:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

Este comando:
- ✅ Muestra todos los logs (incluyendo DEBUG)
- ✅ Recarga automáticamente cuando cambias código (`--reload`)
- ✅ Escucha en todas las interfaces (`--host 0.0.0.0`)
- ✅ Usa el puerto 8000 (`--port 8000`)

## Referencias

- [Uvicorn Logging](https://www.uvicorn.org/settings/#logging)
- [Python Logging Levels](https://docs.python.org/3/library/logging.html#logging-levels)

