# Guía de Conexión a PostgreSQL

## Desde pgAdmin (dentro del contenedor Docker)

Si estás usando pgAdmin que está corriendo en Docker (`http://localhost:8888`), debes usar la siguiente configuración:

- **Host name/address**: `db` (nombre del servicio en docker-compose)
- **Port**: `5432`
- **Maintenance database**: `aiutox_erp_dev`
- **Username**: `devuser`
- **Password**: `devpass`

**NO uses** `localhost` o `127.0.0.1` cuando te conectas desde pgAdmin dentro de Docker.

## Desde herramientas externas (fuera de Docker)

Si estás usando un cliente PostgreSQL desde tu máquina (como DBeaver, DataGrip, psql, etc.), usa:

- **Host**: `localhost` o `127.0.0.1`
- **Port**: `15432` (puerto mapeado en el host)
- **Database**: `aiutox_erp_dev`
- **Username**: `devuser`
- **Password**: `devpass`

## Verificar conexión

### Desde PowerShell (si tienes psql instalado):
```powershell
psql -h localhost -p 15432 -U devuser -d aiutox_erp_dev
```

### Desde Docker (para probar):
```powershell
docker exec -it aiutox_db_dev psql -U devuser -d aiutox_erp_dev
```

## Solución de problemas

Si sigues teniendo problemas de conexión:

1. **Verifica que el contenedor esté corriendo**:
   ```powershell
   docker-compose -f docker-compose.dev.yml ps
   ```

2. **Verifica que el puerto esté escuchando**:
   ```powershell
   netstat -an | Select-String "15432"
   ```

3. **Reinicia el contenedor de PostgreSQL**:
   ```powershell
   docker-compose -f docker-compose.dev.yml restart db
   ```

4. **Verifica los logs**:
   ```powershell
   docker-compose -f docker-compose.dev.yml logs db
   ```

## Configuración actual

- **PostgreSQL dentro de Docker**: `db:5432`
- **PostgreSQL desde el host**: `localhost:15432`
- **Usuario**: `devuser`
- **Contraseña**: `devpass`
- **Base de datos**: `aiutox_erp_dev`


