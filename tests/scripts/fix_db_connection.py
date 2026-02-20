#!/usr/bin/env python3
"""
Script para verificar y arreglar la conexión a la base de datos.
Cambia a SQLite si PostgreSQL no está disponible.
"""

import sys
import time
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

def check_postgres_connection():
    """Verifica si PostgreSQL está disponible."""
    print("🔍 VERIFICANDO CONEXIÓN POSTGRESQL")
    print("=" * 50)

    try:
        import psycopg2
        print("✅ psycopg2 instalado")
    except ImportError:
        print("❌ psycopg2 no instalado")
        return False

    # Intentar conectar con la configuración actual
    try:
        from app.core.config_file import get_settings
        settings = get_settings()

        print(f"📦 Intentando conectar a: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        print(f"📦 Base de datos: {settings.POSTGRES_DB}")
        print(f"📦 Usuario: {settings.POSTGRES_USER}")

        # Timeout de 5 segundos para la conexión
        start_time = time.time()

        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            connect_timeout=5
        )

        elapsed = time.time() - start_time
        print(f"✅ Conexión exitosa en {elapsed:.2f}s")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")
        return False

def create_sqlite_env():
    """Crea un archivo .env con configuración SQLite."""
    print("\n🔧 CREANDO CONFIGURACIÓN SQLITE")
    print("=" * 50)

    env_content = """# Environment
ENV=dev
DEBUG=true

# Database - SQLite para desarrollo rápido
DATABASE_URL=sqlite:///./aiutox_erp_dev.db

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Security
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API URLs
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
"""

    env_path = backend_path / ".env"

    try:
        # Guardar archivo .env
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(env_content)

        print(f"✅ Archivo .env creado en: {env_path}")
        print("✅ Configuración SQLite aplicada")
        return True

    except Exception as e:
        print(f"❌ Error creando .env: {e}")
        return False

def modify_session_py_for_sqlite():
    """Modifica session.py para funcionar bien con SQLite."""
    print("\n🔧 MODIFICANDO session.py PARA SQLITE")
    print("=" * 50)

    session_path = backend_path / "app" / "core" / "db" / "session.py"

    try:
        # Leer el archivo actual
        with open(session_path, encoding="utf-8") as f:
            content = f.read()

        # Verificar si ya está modificado
        if "sqlite" in content.lower():
            print("✅ session.py ya está configurado para SQLite")
            return True

        # Crear versión SQLite-compatible
        sqlite_content = '''from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config_file import get_settings

settings = get_settings()

# Detectar si es SQLite y ajustar configuración
if settings.database_url.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False}  # SQLite specific
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.DEBUG,
        future=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        connect_args={
            "connect_timeout": 10,
            "options": "-c timezone=utc"
        }
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()
'''

        # Guardar la versión modificada
        with open(session_path, "w", encoding="utf-8") as f:
            f.write(sqlite_content)

        print("✅ session.py modificado para SQLite")
        return True

    except Exception as e:
        print(f"❌ Error modificando session.py: {e}")
        return False

def test_sqlite_connection():
    """Prueba la conexión SQLite."""
    print("\n🧪 PROBANDO CONEXIÓN SQLITE")
    print("=" * 50)

    try:
        # Importar después de la configuración
        from app.core.db.session import SessionLocal

        start_time = time.time()
        session = SessionLocal()
        elapsed = time.time() - start_time

        print(f"✅ Sesión SQLite creada en {elapsed:.2f}s")

        # Probar una consulta simple
        from sqlalchemy import text
        result = session.execute(text("SELECT 1"))
        row = result.fetchone()

        session.close()

        if row and row[0] == 1:
            print("✅ Consulta de prueba exitosa")
            return True
        else:
            print("❌ Consulta de prueba falló")
            return False

    except Exception as e:
        print(f"❌ Error probando SQLite: {e}")
        return False

def main():
    """Función principal."""
    print("🔧 DIAGNÓSTICO Y REPARACIÓN DE CONEXIÓN A BASE DE DATOS")
    print("=" * 60)

    # Paso 1: Verificar PostgreSQL
    postgres_available = check_postgres_connection()

    if postgres_available:
        print("\n✅ PostgreSQL está disponible - no se necesitan cambios")
        return True

    # Paso 2: Cambiar a SQLite
    print("\n⚠️ PostgreSQL no disponible - cambiando a SQLite")

    # Crear .env con SQLite
    if not create_sqlite_env():
        print("❌ No se pudo crear el archivo .env")
        return False

    # Modificar session.py
    if not modify_session_py_for_sqlite():
        print("❌ No se pudo modificar session.py")
        return False

    # Probar conexión SQLite
    if not test_sqlite_connection():
        print("❌ La conexión SQLite no funciona")
        return False

    print("\n" + "=" * 60)
    print("✅ REPARACIÓN COMPLETADA")
    print("=" * 60)
    print("✅ Base de datos cambiada a SQLite")
    print("✅ El servidor debería iniciar sin problemas")
    print("💡 Para volver a PostgreSQL, configura un servidor PostgreSQL")
    print("   y elimina el archivo .env")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
