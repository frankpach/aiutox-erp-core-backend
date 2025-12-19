# Script para iniciar los contenedores de desarrollo
# PostgreSQL y Redis para pruebas del backend

# Asegurarse de que estamos en el directorio backend
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptPath

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AiutoX ERP - Desarrollo Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Docker está corriendo
Write-Host "Verificando Docker..." -ForegroundColor Yellow
docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker no está corriendo. Por favor inicia Docker Desktop." -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "[OK] Docker está corriendo" -ForegroundColor Green

# Verificar si existe el archivo .env
Write-Host ""
Write-Host "Verificando archivo .env..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Write-Host "[WARN] Archivo .env no encontrado. Creando desde .env.example..." -ForegroundColor Yellow

    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "[OK] Archivo .env creado desde .env.example" -ForegroundColor Green
        Write-Host ""
        Write-Host "[WARN] IMPORTANTE: Revisa y ajusta el archivo .env con las siguientes configuraciones:" -ForegroundColor Yellow
        Write-Host "  - POSTGRES_HOST=db (para Docker)" -ForegroundColor White
        Write-Host "  - POSTGRES_PORT=5432" -ForegroundColor White
        Write-Host "  - POSTGRES_USER=devuser" -ForegroundColor White
        Write-Host "  - POSTGRES_PASSWORD=devpass" -ForegroundColor White
        Write-Host "  - POSTGRES_DB=aiutox_erp_dev" -ForegroundColor White
        Write-Host "  - REDIS_URL=redis://redis:6379/0 (para Docker)" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "[ERROR] No se encontró .env.example. Por favor crea un archivo .env manualmente." -ForegroundColor Red
        Pop-Location
        exit 1
    }
} else {
    Write-Host "[OK] Archivo .env encontrado" -ForegroundColor Green
}

# Verificar si los contenedores ya están corriendo
Write-Host ""
Write-Host "Verificando estado de los contenedores..." -ForegroundColor Yellow

# Verificar contenedores específicos
$requiredContainers = @("aiutox_db_dev", "aiutox_redis_dev")
$runningContainers = @()
$missingContainers = @()

foreach ($containerName in $requiredContainers) {
    $containerStatus = docker ps --filter "name=$containerName" --format "{{.Names}}" 2>&1
    if ($containerStatus -and $containerStatus -match $containerName) {
        $runningContainers += $containerName
        Write-Host "  [OK] $containerName está corriendo" -ForegroundColor Green
    } else {
        $missingContainers += $containerName
        Write-Host "  [WARN] $containerName NO está corriendo" -ForegroundColor Yellow
    }
}

# Verificar pgAdmin (opcional)
$pgAdminStatus = docker ps --filter "name=aiutox_pgadmin_dev" --format "{{.Names}}" 2>&1
if ($pgAdminStatus -and $pgAdminStatus -match "aiutox_pgadmin_dev") {
    Write-Host "  [OK] aiutox_pgadmin_dev está corriendo" -ForegroundColor Green
} else {
    Write-Host "  [INFO] aiutox_pgadmin_dev no está corriendo (opcional)" -ForegroundColor Gray
}

if ($missingContainers.Count -eq 0) {
    Write-Host ""
    Write-Host "[OK] Todos los contenedores requeridos están corriendo." -ForegroundColor Green
    Write-Host ""
    docker-compose -f docker-compose.dev.yml ps
} else {
    Write-Host ""
    Write-Host "Iniciando contenedores faltantes..." -ForegroundColor Yellow

    # Construir e iniciar los contenedores
    Write-Host ""
    Write-Host "Construyendo e iniciando contenedores..." -ForegroundColor Yellow
    Write-Host "Esto puede tomar unos minutos la primera vez..." -ForegroundColor Gray
    Write-Host ""

    docker-compose -f docker-compose.dev.yml up -d --build

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  [OK] Contenedores iniciados correctamente" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Servicios disponibles:" -ForegroundColor Cyan
        Write-Host "  - PostgreSQL: localhost:15432" -ForegroundColor White
        Write-Host "  - Redis: localhost:6379" -ForegroundColor White
        Write-Host "  - pgAdmin: http://localhost:8888" -ForegroundColor White
        Write-Host "  - Backend API: http://localhost:8000" -ForegroundColor White
        Write-Host ""
        Write-Host "Credenciales pgAdmin:" -ForegroundColor Yellow
        Write-Host "  Email: admin@aiutox.com" -ForegroundColor White
        Write-Host "  Password: password" -ForegroundColor White
        Write-Host ""
        Write-Host "Para ver los logs:" -ForegroundColor Yellow
        Write-Host "  docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Para detener los contenedores:" -ForegroundColor Yellow
        Write-Host "  docker-compose -f docker-compose.dev.yml down" -ForegroundColor Gray
        Write-Host ""

        # Esperar un momento y verificar el estado
        Write-Host ""
        Write-Host "Esperando a que los servicios se inicien completamente..." -ForegroundColor Yellow
        Start-Sleep -Seconds 8

        # Verificar que los servicios estén saludables
        Write-Host ""
        Write-Host "Verificando salud de los servicios..." -ForegroundColor Yellow

        # Verificar PostgreSQL
        $pgReady = $false
        for ($i = 1; $i -le 10; $i++) {
            try {
                $pgTest = docker exec aiutox_db_dev pg_isready -U devuser 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $pgReady = $true
                    Write-Host "  [OK] PostgreSQL está listo" -ForegroundColor Green
                    break
                }
            } catch {
                # Continuar intentando
            }
            if ($i -lt 10) {
                Start-Sleep -Seconds 2
            }
        }
        if (-not $pgReady) {
            Write-Host "  [WARN] PostgreSQL puede no estar completamente listo" -ForegroundColor Yellow
        }

        # Verificar Redis
        $redisReady = $false
        for ($i = 1; $i -le 10; $i++) {
            try {
                $redisTest = docker exec aiutox_redis_dev redis-cli ping 2>&1
                if ($redisTest -match "PONG") {
                    $redisReady = $true
                    Write-Host "  [OK] Redis está listo" -ForegroundColor Green
                    break
                }
            } catch {
                # Continuar intentando
            }
            if ($i -lt 10) {
                Start-Sleep -Seconds 2
            }
        }
        if (-not $redisReady) {
            Write-Host "  [WARN] Redis puede no estar completamente listo" -ForegroundColor Yellow
        }

        Write-Host ""
        Write-Host "Estado final de los contenedores:" -ForegroundColor Cyan
        docker-compose -f docker-compose.dev.yml ps
    } else {
        Write-Host ""
        Write-Host "[ERROR] Error al iniciar los contenedores" -ForegroundColor Red
        Write-Host "Revisa los logs con: docker-compose -f docker-compose.dev.yml logs" -ForegroundColor Yellow
        Pop-Location
        exit 1
    }
}

# Volver al directorio original
Pop-Location
