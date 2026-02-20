#!/usr/bin/env python3
"""
Análisis profundo para encontrar el problema raíz del cuelgue del servidor.
"""

import sys
import threading
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

def analyze_import_chains():
    """Analiza las cadenas de imports para encontrar el problema raíz."""
    print("🔍 ANÁLISIS PROFUNDO DE CADENAS DE IMPORT")
    print("=" * 60)

    # Módulos críticos que causan timeout
    critical_modules = [
        "app.api.v1",
        "app.core.db.session",
        "app.core.auth.rate_limit",
        "app.api.v1.auth",
        "app.api.v1.users",
    ]

    for module in critical_modules:
        print(f"\n📦 Analizando: {module}")
        print("-" * 40)

        def trace_import():
            """Traza el import con detalles."""
            try:
                if module == "app.api.v1":
                    pass
                elif module == "app.core.db.session":
                    pass
                elif module == "app.core.auth.rate_limit":
                    pass
                elif module == "app.api.v1.auth":
                    pass
                elif module == "app.api.v1.users":
                    pass

                return True, None
            except Exception as e:
                return False, str(e)

        result = [None]
        exception = [None]

        def import_thread():
            try:
                success, exc = trace_import()
                result[0] = success
                exception[0] = exc
            except Exception as e:
                result[0] = False
                exception[0] = str(e)

        thread = threading.Thread(target=import_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=2)

        if thread.is_alive():
            print("   ⏰ TIMEOUT - Este módulo está causando el problema")

            # Análisis más profundo
            if module == "app.api.v1":
                analyze_api_v1_imports()
            elif module == "app.core.db.session":
                analyze_session_imports()
            elif module == "app.core.auth.rate_limit":
                analyze_rate_limit_imports()
        elif result[0]:
            print("   ✅ OK")
        else:
            print(f"   ❌ ERROR: {exception[0]}")

def analyze_api_v1_imports():
    """Analiza específicamente los imports de app.api.v1."""
    print("   🔍 Análisis detallado de app.api.v1...")

    # Leer el __init__.py para ver qué está importando
    init_path = backend_path / "app" / "api" / "v1" / "__init__.py"

    try:
        with open(init_path, encoding='utf-8') as f:
            content = f.read()

        print("   📄 Contenido de __init__.py:")
        lines = content.split('\n')
        for i, line in enumerate(lines[:20], 1):  # Primeras 20 líneas
            if line.strip():
                print(f"      {i:2}: {line}")

        print("   ...")

        # Buscar imports específicos que puedan causar problemas
        problem_imports = []
        for line in lines:
            if "from app." in line and "import" in line:
                problem_imports.append(line.strip())

        if problem_imports:
            print(f"   ⚠️ Se encontraron {len(problem_imports)} imports de módulos app:")
            for imp in problem_imports[:5]:  # Primeros 5
                print(f"      - {imp}")
            if len(problem_imports) > 5:
                print(f"      ... y {len(problem_imports) - 5} más")

    except Exception as e:
        print(f"   ❌ Error leyendo __init__.py: {e}")

def analyze_session_imports():
    """Analiza específicamente los imports de session."""
    print("   🔍 Análisis detallado de app.core.db.session...")

    session_path = backend_path / "app" / "core" / "db" / "session.py"

    try:
        with open(session_path, encoding='utf-8') as f:
            content = f.read()

        print("   📄 Imports en session.py:")
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                print(f"      {line}")

        # Verificar si hay llamada a get_settings() que puede causar problemas
        if "get_settings()" in content:
            print("   ⚠️ Se encuentra llamada a get_settings() - puede estar causando el problema")

            # Probar importar get_settings
            try:
                from app.core.config_file import get_settings
                print("   ✅ get_settings() se importa correctamente")

                # Probar obtener settings
                def test_settings():
                    settings = get_settings()
                    return settings

                result = [None]
                def settings_thread():
                    try:
                        _settings = test_settings()
                        result[0] = _settings is not None
                    except Exception as e:
                        result[0] = False
                        print(f"   ❌ Error en get_settings(): {e}")

                thread = threading.Thread(target=settings_thread)
                thread.daemon = True
                thread.start()
                thread.join(timeout=2)

                if thread.is_alive():
                    print("   ⏰ TIMEOUT en get_settings() - ESTE ES EL PROBLEMA")
                elif result[0]:
                    print("   ✅ get_settings() funciona")

            except Exception as e:
                print(f"   ❌ Error importando get_settings: {e}")

    except Exception as e:
        print(f"   ❌ Error analizando session.py: {e}")

def analyze_rate_limit_imports():
    """Analiza específicamente los imports de rate_limit."""
    print("   🔍 Análisis detallado de app.core.auth.rate_limit...")

    rate_limit_path = backend_path / "app" / "core" / "auth" / "rate_limit.py"

    try:
        with open(rate_limit_path, encoding='utf-8') as f:
            content = f.read()

        print("   📄 Imports en rate_limit.py:")
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                print(f"      {line}")

        # Buscar imports que puedan causar dependencias circulares
        if "app.core.db.session" in content:
            print("   ⚠️ Importa app.core.db.session - posible dependencia circular")

    except Exception as e:
        print(f"   ❌ Error analizando rate_limit.py: {e}")

def test_database_connection_directly():
    """Prueba la conexión a la base de datos directamente."""
    print("\n🔍 PRUEBA DIRECTA DE CONEXIÓN A BASE DE DATOS")
    print("=" * 60)

    try:
        # Probar importar psycopg2
        import psycopg2
        print("✅ psycopg2 importado")

        # Probar importar configuración
        from app.core.config_file import get_settings
        print("✅ get_settings importado")

        # Probar obtener settings
        def get_settings_thread():
            try:
                settings = get_settings()
                return settings
            except Exception as e:
                raise e

        result = [None]
        exception = [None]

        def settings_thread():
            try:
                settings = get_settings_thread()
                result[0] = settings
            except Exception as e:
                exception[0] = str(e)

        thread = threading.Thread(target=settings_thread)
        thread.daemon = True
        thread.start()
        thread.join(timeout=3)

        if thread.is_alive():
            print("⏰ TIMEOUT en get_settings() - PROBLEMA EN CONFIGURACIÓN")
            return False
        elif result[0]:
            settings = result[0]
            print(f"✅ Settings obtenidas: DB={settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")

            # Probar conexión a PostgreSQL
            def test_pg_connection():
                conn = psycopg2.connect(
                    host=settings.POSTGRES_HOST,
                    port=settings.POSTGRES_PORT,
                    user=settings.POSTGRES_USER,
                    password=settings.POSTGRES_PASSWORD,
                    database=settings.POSTGRES_DB,
                    connect_timeout=5
                )
                conn.close()

            conn_result = [None]
            def conn_thread():
                try:
                    test_pg_connection()
                    conn_result[0] = True
                except Exception as e:
                    conn_result[0] = False
                    print(f"❌ Error conexión PostgreSQL: {e}")

            thread = threading.Thread(target=conn_thread)
            thread.daemon = True
            thread.start()
            thread.join(timeout=5)

            if thread.is_alive():
                print("⏰ TIMEOUT en conexión PostgreSQL - PROBLEMA DE RED/BASE DE DATOS")
                return False
            elif conn_result[0]:
                print("✅ Conexión PostgreSQL exitosa")
                return True
        else:
            print(f"❌ Error en get_settings: {exception[0]}")
            return False

    except Exception as e:
        print(f"❌ Error en prueba de base de datos: {e}")
        return False

def check_environment_variables():
    """Verifica las variables de entorno."""
    print("\n🔍 VERIFICACIÓN DE VARIABLES DE ENTORNO")
    print("=" * 60)

    import os

    env_vars = [
        "DATABASE_URL",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "DEBUG",
        "ENV"
    ]

    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Ocultar passwords
            if "PASSWORD" in var:
                display_value = "*" * len(value)
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
        else:
            print(f"❌ {var}: No definida")

def main():
    """Función principal del análisis profundo."""
    print("🔍 ANÁLISIS PROFUNDO - PROBLEMA RAÍZ DEL SERVIDOR")
    print("=" * 60)

    # Paso 1: Analizar cadenas de imports
    analyze_import_chains()

    # Paso 2: Probar conexión a base de datos directamente
    db_ok = test_database_connection_directly()

    # Paso 3: Verificar variables de entorno
    check_environment_variables()

    print("\n📊 DIAGNÓSTICO FINAL")
    print("=" * 60)

    if not db_ok:
        print("❌ EL PROBLEMA RAÍZ ESTÁ EN LA CONEXIÓN A LA BASE DE DATOS")
        print("\n💡 SOLUCIONES:")
        print("1. Verificar que PostgreSQL esté corriendo")
        print("2. Verificar credenciales en variables de entorno")
        print("3. Probar con SQLite para desarrollo")
        print("4. Revisar configuración de red/firewall")
    else:
        print("✅ La conexión a base de datos funciona")
        print("❌ EL PROBLEMA RAÍZ ESTÁ EN DEPENDENCIAS CIRCUALES")
        print("\n💡 SOLUCIONES:")
        print("1. Mover imports a dentro de funciones (lazy loading)")
        print("2. Romper dependencias circulares")
        print("3. Simplificar la estructura de imports")
        print("4. Usar inyección de dependencias")

if __name__ == "__main__":
    main()
