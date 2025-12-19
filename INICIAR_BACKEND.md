# Cómo Iniciar el Backend - Guía Completa

## ⚠️ Importante: Comando Correcto

El comando `fastapi dev` requiere `fastapi[standard]` que puede no estar instalado.
**Usa `uvicorn` directamente en su lugar:**

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Opción 1: Usando `uv` (Recomendado)

```bash
cd backend

# 1. Instalar dependencias (si no lo has hecho)
uv sync

# 2. Iniciar servidor
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Opción 2: Usando Python directamente

```bash
cd backend

# 1. Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. Instalar dependencias
pip install -e .

# 3. Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Opción 3: Ejecutar directamente con Python

```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Verificar que el Servidor Está Corriendo

Una vez iniciado, el servidor estará disponible en:
- **API:** http://localhost:8000
- **Documentación Swagger:** http://localhost:8000/docs
- **Documentación ReDoc:** http://localhost:8000/redoc
- **Health Check:** http://localhost:8000/healthz

---

## Notas Importantes

1. **Variables de entorno:** Asegúrate de tener configurado el archivo `.env` en el directorio `backend/`
2. **Base de datos:** El servidor necesita que PostgreSQL esté corriendo y accesible
3. **Redis:** Algunas funcionalidades requieren Redis (opcional para desarrollo básico)
4. **Migraciones:** Ejecuta las migraciones antes de iniciar: `uv run alembic upgrade head`

---

## Solución de Problemas

### Error: "Module not found"
**Solución:** Instala las dependencias con `uv sync` o `pip install -e .`

### Error: "Connection refused" (PostgreSQL)
**Solución:**
1. Verifica que los contenedores Docker estén corriendo: `cd backend && .\start-dev.ps1`
2. Verifica que la URL en `.env` sea correcta:
   ```env
   POSTGRES_HOST=localhost
   POSTGRES_PORT=15432
   ```

### Error: "Port 8000 already in use"
**Solución:**
- Cambia el puerto: `--port 8001`
- O detén el proceso que usa el puerto 8000

### Error: "fastapi[standard] not installed"
**Solución:** Usa `uvicorn` directamente en lugar de `fastapi dev`:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Diferencia entre `fastapi dev` y `uvicorn`

- **`fastapi dev`:** Comando de desarrollo de FastAPI que requiere `fastapi[standard]`
- **`uvicorn`:** Servidor ASGI que ya está incluido en las dependencias del proyecto

**Recomendación:** Usa `uvicorn` directamente ya que está garantizado que está instalado.




