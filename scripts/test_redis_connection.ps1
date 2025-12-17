# Script PowerShell para ejecutar el test de conexión a Redis
# Uso: .\scripts\test_redis_connection.ps1

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test de Conexión a Redis" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio backend
$backendPath = Join-Path $PSScriptRoot ".."
Set-Location $backendPath

Write-Host "📁 Directorio de trabajo: $(Get-Location)" -ForegroundColor Gray
Write-Host ""

# Verificar si Python está disponible
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python no encontrado. Asegúrate de tener Python instalado." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verificar si uv está disponible
try {
    $uvVersion = uv --version 2>&1
    Write-Host "✅ uv encontrado: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️  uv no encontrado. Intentando con python directamente..." -ForegroundColor Yellow
    $useUv = $false
}

Write-Host ""
Write-Host "🚀 Ejecutando test de conexión..." -ForegroundColor Cyan
Write-Host ""

# Ejecutar el script Python
if ($useUv -ne $false) {
    try {
        uv run python scripts/test_redis_connection.py
        $exitCode = $LASTEXITCODE
    } catch {
        Write-Host "❌ Error al ejecutar con uv" -ForegroundColor Red
        Write-Host "Intentando con python directamente..." -ForegroundColor Yellow
        python scripts/test_redis_connection.py
        $exitCode = $LASTEXITCODE
    }
} else {
    python scripts/test_redis_connection.py
    $exitCode = $LASTEXITCODE
}

Write-Host ""

if ($exitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  ✅ Test completado exitosamente" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ❌ Test falló (código: $exitCode)" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

exit $exitCode









