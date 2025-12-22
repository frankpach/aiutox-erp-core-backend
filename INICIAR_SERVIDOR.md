# Cómo Iniciar el Backend con Python

## Opción 1: Usando `uv` (Recomendado)

El proyecto usa `uv` como gestor de paquetes. Es la forma más rápida y recomendada:

```bash
cd backend

# Instalar dependencias (si no lo has hecho)
uv sync

# Instalar dependencias (si no lo has hecho)
uv sync

# Iniciar servidor de desarrollo
# Opción 1: Con uvicorn (recomendado)
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Opción 2: Con fastapi (requiere fastapi[standard])
# uv run fastapi dev app/main.py
```

O con uvicorn directamente:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Opción 2: Usando Python directamente

Si prefieres usar Python directamente (sin `uv`):

```bash
cd backend

# Crear entorno virtual (si no existe)
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -e .

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Opción 3: Ejecutar directamente con Python

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Verificar que el servidor está corriendo

Una vez iniciado, el servidor estará disponible en:
- **API:** http://localhost:8000
- **Documentación Swagger:** http://localhost:8000/docs
- **Documentación ReDoc:** http://localhost:8000/redoc

## Notas Importantes

1. **Variables de entorno:** Asegúrate de tener configurado el archivo `.env` en el directorio `backend/`
2. **Base de datos:** El servidor necesita que PostgreSQL esté corriendo y accesible
3. **Redis:** Algunas funcionalidades requieren Redis (opcional para desarrollo básico)
4. **Migraciones:** Ejecuta las migraciones antes de iniciar: `uv run alembic upgrade head`

## Solución de Problemas

### Error: "Module not found"
**Solución:** Instala las dependencias con `uv sync` o `pip install -e .`

### Error: "Connection refused" (PostgreSQL)
**Solución:** Verifica que PostgreSQL esté corriendo y que la URL en `.env` sea correcta

### Error: "Port 8000 already in use"
**Solución:** Cambia el puerto: `--port 8001` o detén el proceso que usa el puerto 8000










