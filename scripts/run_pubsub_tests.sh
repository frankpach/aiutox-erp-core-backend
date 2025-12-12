#!/bin/bash
# Script bash para ejecutar todos los tests de pub-sub
# Uso: bash scripts/run_pubsub_tests.sh

set -e  # Salir si hay errores

echo ""
echo "========================================"
echo "  Ejecutando Tests del Modulo Pub-Sub"
echo "========================================"
echo ""

# Cambiar al directorio backend
cd "$(dirname "$0")/.." || exit 1

echo "[INFO] Directorio: $(pwd)"
echo ""

# Lista de archivos de test unitarios
UNIT_TESTS=(
    "tests/unit/test_pubsub_client.py"
    "tests/unit/test_pubsub_publisher.py"
    "tests/unit/test_pubsub_consumer.py"
    "tests/unit/test_pubsub_models.py"
    "tests/unit/test_pubsub_errors.py"
    "tests/unit/test_pubsub_groups.py"
    "tests/unit/test_pubsub_retry.py"
)

echo "[TEST] Tests Unitarios"
echo ""

# Ejecutar tests unitarios
# Intentar con uv primero, si no funciona usar python directamente
if command -v uv &> /dev/null; then
    uv run pytest "${UNIT_TESTS[@]}" -v --tb=short --maxfail=5
else
    # Si uv no está disponible, usar python con el venv activado
    if [ -d ".venv" ]; then
        source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
    fi
    python -m pytest "${UNIT_TESTS[@]}" -v --tb=short --maxfail=5
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "[OK] Todos los tests unitarios pasaron"
else
    echo ""
    echo "[ERROR] Algunos tests unitarios fallaron"
    exit 1
fi

echo ""
echo "[TEST] Tests de Integracion (requieren Redis)"
echo ""

# Tests de integración (se saltarán si Redis no está disponible)
INTEGRATION_TESTS=(
    "tests/integration/test_pubsub_integration.py"
)

for test_file in "${INTEGRATION_TESTS[@]}"; do
    if [ -f "$test_file" ]; then
        echo "[INFO] Ejecutando: $test_file"
        if command -v uv &> /dev/null; then
            uv run pytest "$test_file" -v --tb=short -m "redis" || {
        else
            python -m pytest "$test_file" -v --tb=short -m "redis" || {
        fi
            # Exit code 5 = no tests collected (Redis no disponible, se saltan)
            if [ $? -eq 5 ]; then
                echo "[INFO] Tests de integracion se saltaron (Redis no disponible)"
            else
                echo "[WARN] Test de integracion fallo"
            fi
        }
    fi
done

echo ""
echo "[TEST] Tests de API"
echo ""

# Tests de API
API_TESTS=(
    "tests/api/test_pubsub_api.py"
)

for test_file in "${API_TESTS[@]}"; do
    if [ -f "$test_file" ]; then
        echo "[INFO] Ejecutando: $test_file"
        if command -v uv &> /dev/null; then
            uv run pytest "$test_file" -v --tb=short || {
        else
            python -m pytest "$test_file" -v --tb=short || {
        fi
            echo "[WARN] Algunos tests de API fallaron"
        }
    fi
done

echo ""
echo "========================================"
echo "  Resumen de Tests"
echo "========================================"
echo ""
echo "[INFO] Tests unitarios: Ejecutados"
echo "[INFO] Tests de integracion: Ejecutados (se saltan si Redis no esta disponible)"
echo "[INFO] Tests de API: Ejecutados"
echo ""

