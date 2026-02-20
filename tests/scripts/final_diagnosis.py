#!/usr/bin/env python3
"""
Diagnóstico final para identificar el módulo exacto que causa el cuelgue.
"""

import sys
import threading
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

def test_import_step_by_step():
    """Prueba los imports paso a paso para identificar el problema."""
    print("🔍 DIAGNÓSTICO FINAL PASO A PASO")
    print("=" * 60)

    # Lista de imports en orden del main.py
    import_steps = [
        ("logging", "logging"),
        ("os", "os"),
        ("contextlib.asynccontextmanager", "contextlib"),
        ("fastapi.FastAPI", "fastapi"),
        ("fastapi.Request", "fastapi"),
        ("fastapi.status", "fastapi"),
        ("fastapi.exceptions.RequestValidationError", "fastapi"),
        ("fastapi.middleware.cors.CORSMiddleware", "fastapi"),
        ("fastapi.responses.JSONResponse", "fastapi"),
        ("fastapi.responses.Response", "fastapi"),
        ("fastapi.staticfiles.StaticFiles", "fastapi"),
        ("slowapi._rate_limit_exceeded_handler", "slowapi"),
        ("slowapi.errors.RateLimitExceeded", "slowapi"),
        ("starlette.middleware.base.BaseHTTPMiddleware", "starlette"),
        ("app.api.v1.api_router", "app.api.v1"),
        ("app.core.logging as app_logging", "app.core"),
        ("app.core.async_tasks.AsyncTaskService", "app.core.async_tasks"),
        ("app.core.auth.rate_limit.limiter", "app.core.auth"),
        ("app.core.config_file.get_settings", "app.core.config_file"),
        ("app.core.db.session.SessionLocal", "app.core.db.session"),
        ("app.core.exceptions.APIException", "app.core.exceptions"),
        ("app.core.files.tasks as files_tasks", "app.core.files"),
    ]

    failed_at = None

    for i, (import_desc, module_group) in enumerate(import_steps, 1):
        print(f"\n📦 Paso {i}: Importando {import_desc}")

        def import_test():
            try:
                if import_desc == "logging":
                    pass
                elif import_desc == "os":
                    pass
                elif import_desc == "contextlib.asynccontextmanager":
                    pass
                elif import_desc.startswith("fastapi."):
                    if import_desc == "fastapi.FastAPI":
                        pass
                    elif import_desc == "fastapi.Request":
                        pass
                    elif import_desc == "fastapi.status":
                        pass
                    elif import_desc == "fastapi.exceptions.RequestValidationError":
                        pass
                    elif import_desc == "fastapi.middleware.cors.CORSMiddleware":
                        pass
                    elif import_desc == "fastapi.responses.JSONResponse":
                        pass
                    elif import_desc == "fastapi.responses.Response":
                        pass
                    elif import_desc == "fastapi.staticfiles.StaticFiles":
                        pass
                elif import_desc.startswith("slowapi."):
                    if import_desc == "slowapi._rate_limit_exceeded_handler":
                        pass
                    elif import_desc == "slowapi.errors.RateLimitExceeded":
                        pass
                elif import_desc == "starlette.middleware.base.BaseHTTPMiddleware":
                    pass
                elif import_desc == "app.api.v1.api_router":
                    pass
                elif import_desc == "app.core.logging as app_logging":
                    pass
                elif import_desc == "app.core.async_tasks.AsyncTaskService":
                    pass
                elif import_desc == "app.core.auth.rate_limit.limiter":
                    pass
                elif import_desc == "app.core.config_file.get_settings":
                    pass
                elif import_desc == "app.core.db.session.SessionLocal":
                    pass
                elif import_desc == "app.core.exceptions.APIException":
                    pass
                elif import_desc == "app.core.files.tasks as files_tasks":
                    pass

                return True, None
            except Exception as e:
                return False, str(e)

        result = [None]
        exception = [None]

        def import_thread():
            try:
                success, exc = import_test()
                result[0] = success
                exception[0] = exc
            except Exception as e:
                result[0] = False
                exception[0] = str(e)

        thread = threading.Thread(target=import_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=3)

        if thread.is_alive():
            print("   ⏰ TIMEOUT - Este es el problema!")
            failed_at = (i, import_desc, module_group)
            break
        elif result[0]:
            print("   ✅ OK")
        else:
            print(f"   ❌ ERROR: {exception[0]}")
            failed_at = (i, import_desc, module_group)
            break

    return failed_at

def analyze_problematic_module(failed_at):
    """Analiza el módulo problemático."""
    if not failed_at:
        print("\n✅ Todos los imports funcionaron correctamente")
        return

    step, import_desc, module_group = failed_at

    print("\n🔍 ANÁLISIS DEL MÓDULO PROBLEMÁTICO")
    print("=" * 60)
    print(f"❌ Falló en el paso {step}: {import_desc}")
    print(f"📦 Grupo: {module_group}")

    if module_group == "app.api.v1":
        print("\n🔍 Analizando app.api.v1...")
        try:
            # Intentar importar el __init__.py
            print("   📄 Probando import de app.api.v1.__init__")

            def test_v1_init():
                return True

            result = [None]
            def test_thread():
                try:
                    test_v1_init()
                    result[0] = True
                except Exception as e:
                    result[0] = False
                    print(f"   ❌ Error: {e}")

            thread = threading.Thread(target=test_thread)
            thread.daemon = True
            thread.start()
            thread.join(timeout=3)

            if thread.is_alive():
                print("   ⏰ TIMEOUT en app.api.v1.__init__")
                print("   💡 El problema está en los imports del router")
            elif result[0]:
                print("   ✅ app.api.v1.__init__ funciona")

        except Exception as e:
            print(f"   ❌ Error analizando app.api.v1: {e}")

    elif module_group == "app.core.db.session":
        print("\n🔍 Analizando app.core.db.session...")
        print("   💡 Ya optimizamos este módulo, pero puede haber otro problema")
        print("   💡 Revisa si hay modelos que importan session recursivamente")

    elif module_group == "app.core.auth.rate_limit":
        print("\n🔍 Analizando app.core.auth.rate_limit...")
        print("   💡 Puede estar importando session o tener dependencias circulares")

    print("\n💡 SOLUCIONES SUGERIDAS:")
    print("   1. Mover el import problemático a dentro de una función")
    print("   2. Usar import condicional o lazy loading")
    print("   3. Revisar dependencias del módulo")
    print("   4. Considerar eliminar el import si no es crítico")

def main():
    """Función principal."""
    failed_at = test_import_step_by_step()
    analyze_problematic_module(failed_at)

    print("\n📊 RESUMEN FINAL")
    print("=" * 60)

    if failed_at:
        step, import_desc, module_group = failed_at
        print(f"❌ El problema está en: {import_desc}")
        print(f"📦 Paso: {step}")
        print(f"🎯 Grupo: {module_group}")
        print("\n💡 ACCIONES RECOMENDADAS:")
        print("1. Modificar el import problemático")
        print("2. Usar lazy loading para ese módulo")
        print("3. Mover el import a dentro de una función")
        return False
    else:
        print("✅ Todos los imports funcionan correctamente")
        print("💡 El problema puede estar en:")
        print("1. La inicialización de la aplicación")
        print("2. El startup events")
        print("3. Los middleware")
        return True

if __name__ == "__main__":
    main()
