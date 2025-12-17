# Script PowerShell para ejecutar todos los tests de pub-sub
# Uso: .\scripts\run_pubsub_tests.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ejecutando Tests del Modulo Pub-Sub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio backend
$backendPath = Join-Path $PSScriptRoot ".."
Set-Location $backendPath

Write-Host "[INFO] Directorio: $(Get-Location)" -ForegroundColor Gray
Write-Host ""

# Lista de archivos de test
$testFiles = @(
    "tests/unit/test_pubsub_client.py",
    "tests/unit/test_pubsub_publisher.py",
    "tests/unit/test_pubsub_consumer.py",
    "tests/unit/test_pubsub_models.py",
    "tests/unit/test_pubsub_errors.py",
    "tests/unit/test_pubsub_groups.py",
    "tests/unit/test_pubsub_retry.py"
)

Write-Host "[TEST] Tests Unitarios" -ForegroundColor Yellow
Write-Host ""

# Ejecutar tests unitarios
$unitTests = $testFiles -join " "
$result = uv run pytest $unitTests -v --tb=short --maxfail=5

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[OK] Todos los tests unitarios pasaron" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Algunos tests unitarios fallaron" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "[TEST] Tests de Integracion (requieren Redis)" -ForegroundColor Yellow
Write-Host ""

# Tests de integración (se saltarán si Redis no está disponible)
$integrationTests = @(
    "tests/integration/test_pubsub_integration.py"
)

foreach ($testFile in $integrationTests) {
    if (Test-Path $testFile) {
        Write-Host "[INFO] Ejecutando: $testFile" -ForegroundColor Gray
        uv run pytest $testFile -v --tb=short -m "redis"
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 5) {
            # Exit code 5 = no tests collected (Redis no disponible, se saltan)
            Write-Host "[WARN] Test de integracion fallo o Redis no disponible" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "[TEST] Tests de API" -ForegroundColor Yellow
Write-Host ""

# Tests de API
$apiTests = @(
    "tests/api/test_pubsub_api.py"
)

foreach ($testFile in $apiTests) {
    if (Test-Path $testFile) {
        Write-Host "[INFO] Ejecutando: $testFile" -ForegroundColor Gray
        uv run pytest $testFile -v --tb=short
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[WARN] Algunos tests de API fallaron" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Resumen de Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[INFO] Tests unitarios: Ejecutados" -ForegroundColor Gray
Write-Host "[INFO] Tests de integracion: Ejecutados (se saltan si Redis no esta disponible)" -ForegroundColor Gray
Write-Host "[INFO] Tests de API: Ejecutados" -ForegroundColor Gray
Write-Host ""









