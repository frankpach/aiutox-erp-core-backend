#!/usr/bin/env python3
"""
Script detallado para identificar el módulo exacto que causa el cuelgue del servidor.
Prueba cada import individualmente con timeout.
"""

import importlib
import signal
import sys
from contextlib import contextmanager
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))


@contextmanager
def timeout_context(seconds):
    """Context manager para timeout."""

    def timeout_handler(signum, frame):
        raise TimeoutError(f"Import timeout después de {seconds} segundos")

    # Configurar timeout
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restaurar handler original
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def test_import_with_timeout(
    module_name: str, timeout: int = 5
) -> tuple[bool, str, float]:
    """Intenta importar un módulo con timeout."""
    import time

    start_time = time.time()
    try:
        with timeout_context(timeout):
            importlib.import_module(module_name)

        elapsed = time.time() - start_time
        return True, f"OK ({elapsed:.2f}s)", elapsed
    except TimeoutError as e:
        elapsed = time.time() - start_time
        return False, f"TIMEOUT ({elapsed:.2f}s): {e}", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return False, f"ERROR ({elapsed:.2f}s): {e}", elapsed


def main():
    """Diagnóstico detallado con timeout."""
    print("🔍 DIAGNÓSTICO DETALLADO DE IMPORTS CON TIMEOUT")
    print("=" * 60)

    # Lista de módulos en orden de criticidad
    modules_to_test = [
        # Imports básicos del core
        ("app.core.config_file", "Configuración"),
        ("app.core.db.session", "Sesión DB"),
        ("app.core.exceptions", "Excepciones"),
        ("app.core.auth.rate_limit", "Rate limit"),
        # Módulos API v1 básicos
        ("app.api.v1.auth", "Auth API"),
        ("app.api.v1.users", "Users API"),
        ("app.api.v1.config", "Config API"),
        # Módulos de características (features)
        ("app.features.tasks.statuses", "Task Statuses"),
        # Módulos del sistema modular
        ("app.modules.calendar.api", "Calendar API"),
        ("app.modules.crm.api", "CRM API"),
        ("app.modules.inventory.api", "Inventory API"),
        ("app.modules.products.api", "Products API"),
        ("app.modules.tasks.api", "Tasks API"),
        # Resto de APIs v1
        ("app.api.v1.activities", "Activities"),
        ("app.api.v1.activity_icons", "Activity Icons"),
        ("app.api.v1.approvals", "Approvals"),
        ("app.api.v1.automation", "Automation"),
        ("app.api.v1.comments", "Comments"),
        ("app.api.v1.contact_methods", "Contact Methods"),
        ("app.api.v1.files", "Files"),
        ("app.api.v1.flow_runs", "Flow Runs"),
        ("app.api.v1.folders", "Folders"),
        ("app.api.v1.import_export", "Import/Export"),
        ("app.api.v1.integrations", "Integrations"),
        ("app.api.v1.notifications", "Notifications"),
        ("app.api.v1.preferences", "Preferences"),
        ("app.api.v1.pubsub", "PubSub"),
        ("app.api.v1.reporting", "Reporting"),
        ("app.api.v1.search", "Search"),
        ("app.api.v1.sse", "SSE"),
        ("app.api.v1.tags", "Tags"),
        ("app.api.v1.templates", "Templates"),
        ("app.api.v1.views", "Views"),
        ("app.api.v1.workflows", "Workflows"),
        # Import completo del router
        ("app.api.v1", "API v1 Router"),
        ("app.api.v1.api_router", "API Router Instance"),
        # Import del main
        ("app.main", "Main App"),
    ]

    print("\n🧪 PROBANDO IMPORTS INDIVIDUALES")
    print("-" * 40)

    failed_modules = []
    timeout_modules = []
    total_time = 0

    for module_name, description in modules_to_test:
        print(f"\n📦 {description} ({module_name})")
        print("   ", end="", flush=True)

        success, result, elapsed = test_import_with_timeout(module_name, timeout=3)
        total_time += elapsed

        if success:
            print(f"✅ {result}")
        elif "TIMEOUT" in result:
            print(f"⏰ {result}")
            timeout_modules.append((module_name, description, elapsed))
        else:
            print(f"❌ {result}")
            failed_modules.append((module_name, description, result))

    # Resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DEL DIAGNÓSTICO")
    print("=" * 60)

    total_modules = len(modules_to_test)
    successful = total_modules - len(failed_modules) - len(timeout_modules)

    print(f"Total módulos probados: {total_modules}")
    print(f"✅ Exitosos: {successful}")
    print(f"❌ Fallidos: {len(failed_modules)}")
    print(f"⏰ Timeout: {len(timeout_modules)}")
    print(f"⏱️ Tiempo total: {total_time:.2f}s")

    # Módulos con timeout (sospechosos de cuelgue)
    if timeout_modules:
        print("\n⚠️ MÓDULOS CON TIMEOUT (SOSPECHOSOS):")
        for module_name, description, elapsed in timeout_modules:
            print(f"   ⏰ {description}: {module_name} ({elapsed:.2f}s)")

    # Módulos con errores
    if failed_modules:
        print("\n❌ MÓDULOS CON ERRORES:")
        for module_name, description, error in failed_modules:
            print(f"   ❌ {description}: {module_name}")
            print(f"      Error: {error}")

    # Recomendaciones
    print("\n💡 RECOMENDACIONES:")
    if timeout_modules:
        print("   1. Los módulos con timeout son los sospechosos principales")
        print("   2. Revisa dependencias circulares en estos módulos")
        print("   3. Verifica imports de módulos externos o de base de datos")
    elif failed_modules:
        print("   1. Corrige los errores de importación primero")
        print("   2. Verifica que los archivos existan")
    else:
        print("   1. Todos los imports funcionan correctamente")
        print("   2. El problema puede estar en el startup del servidor")

    return len(timeout_modules) == 0 and len(failed_modules) == 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Diagnóstico interrumpido por el usuario")
        sys.exit(130)
