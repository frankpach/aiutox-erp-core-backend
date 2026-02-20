#!/usr/bin/env python3
"""
Diagnóstico ultra-minimalista para encontrar el problema fundamental.
"""

import sys
import threading
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

def test_basic_python():
    """Prueba si Python básico funciona."""
    print("🔍 PRUEBA 1: Python básico")
    print("-" * 40)

    try:
        print("✅ Módulos estándar de Python funcionan")
        return True
    except Exception as e:
        print(f"❌ Error en Python básico: {e}")
        return False

def test_fastapi_minimal():
    """Prueba FastAPI mínimo."""
    print("\n🔍 PRUEBA 2: FastAPI mínimo")
    print("-" * 40)

    try:
        def import_fastapi():
            from fastapi import FastAPI
            app = FastAPI()
            return app

        result = [None]
        def fastapi_thread():
            try:
                app = import_fastapi()
                result[0] = True
            except Exception as e:
                result[0] = False
                print(f"❌ Error importando FastAPI: {e}")

        thread = threading.Thread(target=fastapi_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=3)

        if thread.is_alive():
            print("⏰ TIMEOUT importando FastAPI")
            return False
        elif result[0]:
            print("✅ FastAPI funciona")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error en prueba FastAPI: {e}")
        return False

def test_environment():
    """Prueba variables de entorno y configuración."""
    print("\n🔍 PRUEBA 3: Variables de entorno")
    print("-" * 40)

    try:
        import os

        # Listar variables de entorno relevantes
        env_vars = ["PATH", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_DEFAULT_ENV"]

        for var in env_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: {value[:50]}...")
            else:
                print(f"❌ {var}: No definida")

        return True

    except Exception as e:
        print(f"❌ Error en variables de entorno: {e}")
        return False

def test_path_issues():
    """Prueba problemas de PATH o directorios."""
    print("\n🔍 PRUEBA 4: PATH y directorios")
    print("-" * 40)

    try:
        import os
        import sys

        print(f"📁 Directorio actual: {os.getcwd()}")
        print(f"📁 Python PATH: {len(sys.path)} entradas")

        # Verificar si el directorio backend está en PATH
        backend_str = str(backend_path)
        found_in_path = any(backend_str in p for p in sys.path)

        if found_in_path:
            print("✅ Directorio backend está en PATH")
        else:
            print("❌ Directorio backend NO está en PATH")

        # Verificar si existe el directorio app
        app_dir = backend_path / "app"
        if app_dir.exists():
            print("✅ Directorio app existe")
        else:
            print("❌ Directorio app NO existe")

        return True

    except Exception as e:
        print(f"❌ Error en PATH: {e}")
        return False

def test_import_without_app():
    """Prueba importar algo que no esté en app."""
    print("\n🔍 PRUEBA 5: Import fuera de app")
    print("-" * 40)

    try:
        # Intentar importar algo que no esté en la estructura app
        def test_import():
            return True

        result = [None]
        def import_thread():
            try:
                success = test_import()
                result[0] = success
            except Exception as e:
                result[0] = False
                print(f"❌ Error importando requests: {e}")

        thread = threading.Thread(target=import_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=2)

        if thread.is_alive():
            print("⏰ TIMEOUT importando requests")
            return False
        elif result[0]:
            print("✅ Import fuera de app funciona")
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Error en prueba: {e}")
        return False

def create_ultra_emergency_server():
    """Crea un servidor ultra-emergencia sin imports de app."""
    print("\n🚨 CREANDO SERVIDOR ULTRA-EMERGENCIA")
    print("=" * 50)

    ultra_emergency_content = '''"""
Servidor ultra-emergencia - sin absolutamente nada de app.
"""

# Solo importar lo esencial
try:
    from fastapi import FastAPI
    print("✅ FastAPI importado")
except Exception as e:
    print(f"❌ Error importando FastAPI: {e}")
    raise

# Crear aplicación sin absolutamente nada más
app = FastAPI(title="Ultra Emergency Server")

@app.get("/")
def root():
    return {"message": "Ultra emergency server", "status": "working"}

@app.get("/test")
def test():
    return {"test": "ok", "timestamp": "now"}

if __name__ == "__main__":
    try:
        import uvicorn
        print("✅ Uvicorn importado")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print(f"❌ Error importando uvicorn: {e}")
        raise
'''

    ultra_emergency_path = backend_path / "ultra_emergency_server.py"

    try:
        with open(ultra_emergency_path, 'w', encoding='utf-8') as f:
            f.write(ultra_emergency_content)

        print(f"✅ Ultra emergency server creado en: {ultra_emergency_path}")
        return True

    except Exception as e:
        print(f"❌ Error creando ultra emergency server: {e}")
        return False

def main():
    """Función principal del diagnóstico ultra-minimalista."""
    print("🔍 DIAGNÓSTICO ULTRA-MINIMALISTA")
    print("=" * 60)
    print("Buscando el problema FUNDAMENTAL...")

    # Pruebas básicas
    tests = [
        ("Python básico", test_basic_python),
        ("FastAPI mínimo", test_fastapi_minimal),
        ("Variables de entorno", test_environment),
        ("PATH y directorios", test_path_issues),
        ("Import fuera de app", test_import_without_app),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error en prueba {test_name}: {e}")
            results.append((test_name, False))

    # Resumen
    print("\n📊 RESUMEN DE PRUEBAS")
    print("=" * 60)

    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")

    # Crear servidor ultra-emergencia
    create_ultra_emergency_server()

    print("\n💡 PRÓXIMO PASO:")
    print("1. Ejecuta el servidor ultra-emergencia:")
    print("   python ultra_emergency_server.py")
    print("2. Si esto funciona, el problema está en los imports de app")
    print("3. Si esto NO funciona, el problema está en FastAPI/uvicorn/entorno")

if __name__ == "__main__":
    main()
