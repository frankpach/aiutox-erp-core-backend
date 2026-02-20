#!/usr/bin/env python3
"""
Script específico para diagnosticar el problema con app.core.db.session
"""

import sys
import time
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

def test_db_session_import():
    """Prueba detallada del import de session.py"""
    print("🔍 DIAGNÓSTICO ESPECÍFICO: app.core.db.session")
    print("=" * 60)

    # Paso 1: Importar dependencias básicas
    print("\n📦 Paso 1: Importando dependencias básicas...")
    try:
        print("   ✅ os")

        from sqlalchemy import create_engine
        print("   ✅ sqlalchemy.create_engine")

        print("   ✅ sqlalchemy.ext.declarative.declarative_base")

        print("   ✅ sqlalchemy.orm.sessionmaker")

        from sqlalchemy.pool import StaticPool
        print("   ✅ sqlalchemy.pool.StaticPool")

    except Exception as e:
        print(f"   ❌ Error en dependencias básicas: {e}")
        return False

    # Paso 2: Importar configuración
    print("\n📦 Paso 2: Importando configuración...")
    try:
        from app.core.config_file import get_settings
        print("   ✅ app.core.config_file.get_settings")

        settings = get_settings()
        print(f"   ✅ settings obtenidas (DEBUG={settings.DEBUG})")

    except Exception as e:
        print(f"   ❌ Error en configuración: {e}")
        return False

    # Paso 3: Probar crear engine manualmente
    print("\n📦 Paso 3: Probando crear engine manualmente...")
    try:
        start_time = time.time()

        # Usar SQLite para prueba (más rápido)
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False
        )
        assert engine is not None

        elapsed = time.time() - start_time
        print(f"   ✅ Engine creado manualmente en {elapsed:.2f}s")

    except Exception as e:
        print(f"   ❌ Error creando engine: {e}")
        return False

    # Paso 4: Intentar importar session.py
    print("\n📦 Paso 4: Intentando importar app.core.db.session...")
    try:
        start_time = time.time()

        # Importar con timeout manual
        import threading
        result = [None]
        exception = [None]

        def import_session():
            try:
                result[0] = True
            except Exception as e:
                exception[0] = e
                result[0] = False

        thread = threading.Thread(target=import_session)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5)

        elapsed = time.time() - start_time

        if thread.is_alive():
            print(f"   ⏰ TIMEOUT después de {elapsed:.2f}s")
            return False
        elif result[0]:
            print(f"   ✅ Import exitoso en {elapsed:.2f}s")

            # Paso 5: Probar usar SessionLocal
            print("\n📦 Paso 5: Probando usar SessionLocal...")
            try:
                from app.core.db.session import SessionLocal

                start_time = time.time()
                session = SessionLocal()
                elapsed = time.time() - start_time

                print(f"   ✅ SessionLocal() creada en {elapsed:.2f}s")

                session.close()
                print("   ✅ Sesión cerrada correctamente")

                return True

            except Exception as e:
                print(f"   ❌ Error usando SessionLocal: {e}")
                return False
        else:
            print(f"   ❌ Error importando session: {exception[0]}")
            return False

    except Exception as e:
        print(f"   ❌ Error en prueba de import: {e}")
        return False

def main():
    """Función principal."""
    success = test_db_session_import()

    print("\n" + "=" * 60)
    print("📊 RESUMEN")
    print("=" * 60)

    if success:
        print("✅ app.core.db.session funciona correctamente")
        print("💡 El problema puede estar en otro lugar")
    else:
        print("❌ app.core.db.session tiene problemas")
        print("💡 Revisa:")
        print("   1. Configuración de base de datos")
        print("   2. Dependencias circulares")
        print("   3. Conexión a la base de datos")

    return success

if __name__ == "__main__":
    main()
