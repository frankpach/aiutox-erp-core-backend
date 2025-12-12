# Test de Conexión a Redis

Scripts interactivos para verificar la configuración y conexión a Redis.

## 🚀 Uso Rápido desde PowerShell

### Opción 1: Script PowerShell (Recomendado)
```powershell
cd backend
.\scripts\test_redis_connection.ps1
```

### Opción 2: Python directamente
```powershell
cd backend
python scripts/test_redis_connection.py
```

### Opción 3: Con uv
```powershell
cd backend
uv run python scripts/test_redis_connection.py
```

## 📋 Qué verifica el script

1. **Configuración actual**: Muestra la URL y configuración de Redis
2. **Conexión**: Intenta conectar a Redis con timeout de 5 segundos
3. **Información del servidor**: Versión, uptime, memoria, etc.
4. **Streams**: Verifica si los streams necesarios existen
5. **Publicación de evento** (opcional): Prueba publicar un evento de prueba

## ⚙️ Configuración de Redis

### Variables de entorno

El script lee la configuración desde:
- Archivo `.env` en el directorio `backend/`
- Variables de entorno del sistema

Variables necesarias:
```env
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
```

### Configuración por defecto

Si no se configuran las variables, el sistema usa:
- `REDIS_URL`: `redis://localhost:6379/0`
- `REDIS_PASSWORD`: (vacío)

## 🔧 Solución de Problemas

### Error: "Timeout: Redis no respondió"

**Causas posibles:**
- Redis no está corriendo
- Puerto incorrecto
- Firewall bloqueando la conexión

**Soluciones:**
1. Verificar que Redis esté corriendo:
   ```powershell
   # Si Redis está en Docker
   docker ps | findstr redis

   # Si Redis está instalado localmente
   redis-cli ping
   ```

2. Verificar el puerto:
   ```powershell
   # Verificar qué está escuchando en el puerto 6379
   netstat -an | findstr 6379
   ```

3. Si Redis está en Docker, verificar la configuración:
   ```yaml
   # docker-compose.yml
   redis:
     image: redis:7-alpine
     ports:
       - "6379:6379"
   ```

### Error: "Conexión rechazada"

**Causas:**
- Redis no está escuchando en esa dirección
- Puerto incorrecto
- Redis está en otro host

**Soluciones:**
1. Verificar la URL de conexión en `.env`
2. Si Redis está en otro host, usar: `redis://hostname:6379/0`
3. Verificar que Redis esté configurado para aceptar conexiones externas

### Error: "Error al importar módulos"

**Causas:**
- No estás en el directorio correcto
- Dependencias no instaladas

**Soluciones:**
```powershell
cd backend
uv sync --extra dev
```

## 📊 Ejemplo de Salida Exitosa

```
======================================================================
🔍 Verificación de Conexión a Redis
======================================================================

📋 Configuración actual:
   REDIS_URL: redis://localhost:6379/0
   REDIS_PASSWORD: (vacío)
   REDIS_STREAM_DOMAIN: events:domain
   REDIS_STREAM_TECHNICAL: events:technical
   REDIS_STREAM_FAILED: events:failed

🔄 Intentando conectar a Redis...
   ⏳ Esperando respuesta (timeout: 5 segundos)...
   ✅ ¡Conexión exitosa!

📊 Información del servidor Redis:
   Versión: 7.2.0
   Modo: standalone
   Uptime (días): 5
   Memoria usada: 1.2M
   Clientes conectados: 1

🔍 Verificando streams...
   ⚠️  events:domain: No existe (se creará automáticamente)
   ⚠️  events:technical: No existe (se creará automáticamente)
   ⚠️  events:failed: No existe (se creará automáticamente)

======================================================================
✅ Redis está configurado correctamente y funcionando
======================================================================
```

## 🐳 Redis en Docker

Si usas Docker, asegúrate de que el contenedor esté corriendo:

```powershell
# Iniciar Redis
docker-compose up -d redis

# Ver logs
docker-compose logs redis

# Verificar que está corriendo
docker ps | findstr redis
```

## 📝 Notas

- El script usa timeouts para evitar que se cuelgue
- Si Redis no está disponible, el script te dará información útil para solucionarlo
- Los streams se crean automáticamente cuando se publica el primer evento
- El script es interactivo y te preguntará si quieres probar la publicación de eventos


