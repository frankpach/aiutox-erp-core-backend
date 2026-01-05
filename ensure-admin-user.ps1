# Script para asegurar que el usuario admin@aiutox.com existe y tiene rol de admin
# Ejecutar desde el directorio backend

Write-Host "[INFO] Verificando usuario admin..." -ForegroundColor Cyan

# Activar entorno virtual si existe
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "[INFO] Activando entorno virtual..." -ForegroundColor Cyan
    & .\venv\Scripts\Activate.ps1
}

# Ejecutar script Python
python ensure_admin_user.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Verificación completada exitosamente!" -ForegroundColor Green
} else {
    Write-Host "`n[ERROR] La verificación falló. Revisa los mensajes de error arriba." -ForegroundColor Red
    exit 1
}





















