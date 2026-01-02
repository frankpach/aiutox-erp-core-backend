# Script para verificar la integración entre Backend, PostgreSQL, Redis y Frontend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verificación de Integración" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()

# Función para verificar puerto
function Test-Port {
    param([int]$Port, [string]$ServiceName)

    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
        return $connection
    } catch {
        return $false
    }
}

# Función para verificar HTTP endpoint
function Test-HttpEndpoint {
    param([string]$Url, [string]$ServiceName)

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

# ========================================
# 1. Verificar Docker y Contenedores
# ========================================
Write-Host "1. Verificando Docker y contenedores..." -ForegroundColor Yellow

docker info | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "   [OK] Docker está corriendo" -ForegroundColor Green

    # Verificar contenedores
    $containers = docker ps --format "{{.Names}}" 2>&1
    if ($containers -match "aiutox") {
        Write-Host "   [OK] Contenedores AiutoX están corriendo" -ForegroundColor Green
    } else {
        $warnings += "Contenedores Docker no están corriendo"
        Write-Host "   [WARN] Contenedores Docker no están corriendo" -ForegroundColor Yellow
    }
} else {
    $errors += "Docker no está corriendo"
    Write-Host "   [ERROR] Docker no está corriendo" -ForegroundColor Red
}

# ========================================
# 2. Verificar PostgreSQL
# ========================================
Write-Host ""
Write-Host "2. Verificando PostgreSQL..." -ForegroundColor Yellow

if (Test-Port -Port 15432 -ServiceName "PostgreSQL") {
    Write-Host "   [OK] PostgreSQL está escuchando en puerto 15432" -ForegroundColor Green

    # Intentar conexión desde Python
    Push-Location backend
    $dbTest = python test_app_db_connection.py 2>&1
    Pop-Location

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [OK] Conexión a PostgreSQL exitosa" -ForegroundColor Green
    } else {
        $errors += "No se puede conectar a PostgreSQL"
        Write-Host "   [ERROR] No se puede conectar a PostgreSQL" -ForegroundColor Red
        Write-Host "   Detalles: $dbTest" -ForegroundColor Gray
    }
} else {
    $errors += "PostgreSQL no está escuchando en puerto 15432"
    Write-Host "   [ERROR] PostgreSQL no está escuchando en puerto 15432" -ForegroundColor Red
}

# ========================================
# 3. Verificar Redis
# ========================================
Write-Host ""
Write-Host "3. Verificando Redis..." -ForegroundColor Yellow

if (Test-Port -Port 6379 -ServiceName "Redis") {
    Write-Host "   [OK] Redis está escuchando en puerto 6379" -ForegroundColor Green

    # Intentar conexión desde Python
    Push-Location backend
    $redisTest = python scripts/test_redis_connection.py 2>&1
    Pop-Location

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [OK] Conexión a Redis exitosa" -ForegroundColor Green
    } else {
        $warnings += "No se puede conectar a Redis (opcional)"
        Write-Host "   [WARN] No se puede conectar a Redis (opcional)" -ForegroundColor Yellow
    }
} else {
    $warnings += "Redis no está escuchando en puerto 6379 (opcional)"
    Write-Host "   [WARN] Redis no está escuchando (opcional)" -ForegroundColor Yellow
}

# ========================================
# 4. Verificar Backend API
# ========================================
Write-Host ""
Write-Host "4. Verificando Backend API..." -ForegroundColor Yellow

if (Test-Port -Port 8000 -ServiceName "Backend") {
    Write-Host "   [OK] Backend está escuchando en puerto 8000" -ForegroundColor Green

    # Verificar health endpoint
    if (Test-HttpEndpoint -Url "http://localhost:8000/healthz" -ServiceName "Backend Health") {
        Write-Host "   [OK] Endpoint /healthz responde correctamente" -ForegroundColor Green
    } else {
        $errors += "Backend /healthz no responde"
        Write-Host "   [ERROR] Endpoint /healthz no responde" -ForegroundColor Red
    }

    # Verificar docs endpoint
    if (Test-HttpEndpoint -Url "http://localhost:8000/docs" -ServiceName "Backend Docs") {
        Write-Host "   [OK] Endpoint /docs (Swagger) accesible" -ForegroundColor Green
    } else {
        $warnings += "Backend /docs no accesible"
        Write-Host "   [WARN] Endpoint /docs no accesible" -ForegroundColor Yellow
    }
} else {
    $errors += "Backend no está escuchando en puerto 8000"
    Write-Host "   [ERROR] Backend no está escuchando en puerto 8000" -ForegroundColor Red
}

# ========================================
# 5. Verificar Frontend
# ========================================
Write-Host ""
Write-Host "5. Verificando Frontend..." -ForegroundColor Yellow

if (Test-Port -Port 3000 -ServiceName "Frontend") {
    Write-Host "   [OK] Frontend está escuchando en puerto 3000" -ForegroundColor Green

    # Verificar que responde
    if (Test-HttpEndpoint -Url "http://127.0.0.1:3000" -ServiceName "Frontend") {
        Write-Host "   [OK] Frontend responde correctamente" -ForegroundColor Green
    } else {
        $warnings += "Frontend no responde correctamente"
        Write-Host "   [WARN] Frontend no responde correctamente" -ForegroundColor Yellow
    }
} else {
    $warnings += "Frontend no está escuchando en puerto 3000"
    Write-Host "   [WARN] Frontend no está escuchando en puerto 3000" -ForegroundColor Yellow
}

# ========================================
# 6. Verificar Configuración
# ========================================
Write-Host ""
Write-Host "6. Verificando archivos de configuración..." -ForegroundColor Yellow

# Verificar backend/.env
if (Test-Path "backend/.env") {
    Write-Host "   [OK] backend/.env existe" -ForegroundColor Green

    # Verificar variables importantes
    $envContent = Get-Content "backend/.env" -Raw
    if ($envContent -match "POSTGRES_HOST") {
        Write-Host "   [OK] POSTGRES_HOST configurado" -ForegroundColor Green
    } else {
        $warnings += "POSTGRES_HOST no encontrado en backend/.env"
        Write-Host "   [WARN] POSTGRES_HOST no encontrado" -ForegroundColor Yellow
    }

    if ($envContent -match "CORS_ORIGINS") {
        Write-Host "   [OK] CORS_ORIGINS configurado" -ForegroundColor Green
    } else {
        $warnings += "CORS_ORIGINS no encontrado en backend/.env"
        Write-Host "   [WARN] CORS_ORIGINS no encontrado" -ForegroundColor Yellow
    }
} else {
    $errors += "backend/.env no existe"
    Write-Host "   [ERROR] backend/.env no existe" -ForegroundColor Red
}

# Verificar frontend/.env.local
if (Test-Path "frontend/.env.local") {
    Write-Host "   [OK] frontend/.env.local existe" -ForegroundColor Green

    $frontendEnv = Get-Content "frontend/.env.local" -Raw
    if ($frontendEnv -match "VITE_API_BASE_URL") {
        Write-Host "   [OK] VITE_API_BASE_URL configurado" -ForegroundColor Green
    } else {
        $warnings += "VITE_API_BASE_URL no encontrado en frontend/.env.local"
        Write-Host "   [WARN] VITE_API_BASE_URL no encontrado" -ForegroundColor Yellow
    }
} else {
    $warnings += "frontend/.env.local no existe (puede usar defaults)"
    Write-Host "   [WARN] frontend/.env.local no existe (puede usar defaults)" -ForegroundColor Yellow
}

# ========================================
# Resumen
# ========================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RESUMEN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($errors.Count -eq 0) {
    Write-Host "[OK] No se encontraron errores críticos" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Se encontraron $($errors.Count) error(es) crítico(s):" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "[WARN] Se encontraron $($warnings.Count) advertencia(s):" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "  - $warning" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Para más detalles, consulta: ANALISIS_INTEGRACION.md" -ForegroundColor Cyan
Write-Host ""






















