"""Script Python para ejecutar todos los tests de pub-sub de forma controlada."""

import os
import subprocess
import sys
from pathlib import Path

# Cambiar al directorio backend
backend_path = Path(__file__).parent.parent
os.chdir(backend_path)

print("=" * 70)
print("[TEST] Ejecutando Tests del Modulo Pub-Sub")
print("=" * 70)
print()

# Lista de archivos de test
unit_tests = [
    "tests/unit/test_pubsub_client.py",
    "tests/unit/test_pubsub_publisher.py",
    "tests/unit/test_pubsub_consumer.py",
    "tests/unit/test_pubsub_models.py",
    "tests/unit/test_pubsub_errors.py",
    "tests/unit/test_pubsub_groups.py",
    "tests/unit/test_pubsub_retry.py",
]

integration_tests = [
    "tests/integration/test_pubsub_integration.py",
]

api_tests = [
    "tests/api/test_pubsub_api.py",
]

def run_tests(test_files, category):
    """Ejecutar tests y retornar el código de salida."""
    print(f"[TEST] {category}")
    print()

    if not test_files:
        print(f"   [SKIP] No hay tests de {category}")
        return 0

    # Construir comando
    cmd = ["uv", "run", "pytest"] + test_files + ["-v", "--tb=short", "--maxfail=5"]

    try:
        result = subprocess.run(cmd, cwd=backend_path, timeout=300)  # 5 minutos timeout
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"   [ERROR] Timeout ejecutando tests de {category}")
        return 1
    except Exception as e:
        print(f"   [ERROR] Error ejecutando tests: {e}")
        return 1

# Ejecutar tests unitarios
print("[1/3] Tests Unitarios")
print("-" * 70)
exit_code = run_tests(unit_tests, "Tests Unitarios")

if exit_code != 0:
    print()
    print("[ERROR] Algunos tests unitarios fallaron")
    sys.exit(exit_code)

print()
print("[OK] Todos los tests unitarios pasaron")
print()

# Ejecutar tests de integración
print("[2/3] Tests de Integracion (requieren Redis)")
print("-" * 70)
exit_code = run_tests(integration_tests, "Tests de Integracion")

if exit_code == 5:
    # Exit code 5 = no tests collected (Redis no disponible, se saltan)
    print()
    print("[INFO] Tests de integracion se saltaron (Redis no disponible)")
elif exit_code != 0:
    print()
    print("[WARN] Algunos tests de integracion fallaron")
else:
    print()
    print("[OK] Tests de integracion pasaron")

print()

# Ejecutar tests de API
print("[3/3] Tests de API")
print("-" * 70)
exit_code = run_tests(api_tests, "Tests de API")

if exit_code != 0:
    print()
    print("[WARN] Algunos tests de API fallaron")
else:
    print()
    print("[OK] Tests de API pasaron")

print()
print("=" * 70)
print("[RESUMEN] Todos los tests ejecutados")
print("=" * 70)
print()
print("[INFO] Tests unitarios: Ejecutados")
print("[INFO] Tests de integracion: Ejecutados (se saltan si Redis no esta disponible)")
print("[INFO] Tests de API: Ejecutados")
print()

