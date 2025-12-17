# Script para iniciar los contenedores de desarrollo
# PostgreSQL y Redis para pruebas del backend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AiutoX ERP - Desarrollo Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Docker está corriendo
Write-Host "Verificando Docker..." -ForegroundColor Yellow
docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Docker no está corriendo. Por favor inicia Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "✓ Docker está corriendo" -ForegroundColor Green

# Verificar si existe el archivo .env
Write-Host ""
Write-Host "Verificando archivo .env..." -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Write-Host "⚠ Archivo .env no encontrado. Creando desde .env.example..." -ForegroundColor Yellow

    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "✓ Archivo .env creado desde .env.example" -ForegroundColor Green
        Write-Host ""
        Write-Host "⚠ IMPORTANTE: Revisa y ajusta el archivo .env con las siguientes configuraciones:" -ForegroundColor Yellow
        Write-Host "  - POSTGRES_HOST=db (para Docker)" -ForegroundColor White
        Write-Host "  - POSTGRES_PORT=5432" -ForegroundColor White
        Write-Host "  - POSTGRES_USER=devuser" -ForegroundColor White
        Write-Host "  - POSTGRES_PASSWORD=devpass" -ForegroundColor White
        Write-Host "  - POSTGRES_DB=aiutox_erp_dev" -ForegroundColor White
        Write-Host "  - REDIS_URL=redis://redis:6379/0 (para Docker)" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "✗ No se encontró .env.example. Por favor crea un archivo .env manualmente." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Archivo .env encontrado" -ForegroundColor Green
}

# Detener contenedores existentes si están corriendo
Write-Host ""
Write-Host "Deteniendo contenedores existentes (si hay alguno)..." -ForegroundColor Yellow
docker-compose -f docker-compose.dev.yml down 2>&1 | Out-Null

# Construir e iniciar los contenedores
Write-Host ""
Write-Host "Construyendo e iniciando contenedores..." -ForegroundColor Yellow
Write-Host "Esto puede tomar unos minutos la primera vez..." -ForegroundColor Gray
Write-Host ""

docker-compose -f docker-compose.dev.yml up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✓ Contenedores iniciados correctamente" -ForegroundColor Green
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
    Write-Host "Verificando estado de los servicios..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5

    Write-Host ""
    docker-compose -f docker-compose.dev.yml ps
} else {
    Write-Host ""
    Write-Host "✗ Error al iniciar los contenedores" -ForegroundColor Red
    Write-Host "Revisa los logs con: docker-compose -f docker-compose.dev.yml logs" -ForegroundColor Yellow
    exit 1
}

