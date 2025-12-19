#!/bin/bash
# Script bash para ejecutar TODOS los tests del proyecto
# Uso: bash scripts/run_all_tests.sh

set -e

echo ""
echo "========================================"
echo "  Ejecutando TODOS los Tests"
echo "========================================"
echo ""

cd "$(dirname "$0")/.." || exit 1

echo "[INFO] Directorio: $(pwd)"
echo ""

# Ejecutar todos los tests
echo "[TEST] Ejecutando todos los tests..."
echo ""

uv run pytest tests/ -v --tb=short --maxfail=10

echo ""
echo "========================================"
echo "  Tests Completados"
echo "========================================"
echo ""










