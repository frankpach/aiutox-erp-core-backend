#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para probar la conexión a PostgreSQL usando SQLAlchemy (como el backend)."""

import sys
import os

# Configurar codificación UTF-8 para Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    print("ERROR: SQLAlchemy no esta instalado.")
    print("Instalalo con: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)


def test_sqlalchemy_connection(database_url):
    """Prueba la conexion usando SQLAlchemy."""
    print(f"\n{'='*60}")
    print(f"Probando conexion con SQLAlchemy")
    print(f"{'='*60}")
    print(f"URL: {database_url.replace('devpass', '***')}")
    print(f"{'='*60}\n")

    try:
        # Crear engine
        engine = create_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5}
        )

        # Probar conexion
        with engine.connect() as conn:
            print("[OK] Conexion exitosa con SQLAlchemy!\n")

            # Prueba 1: Informacion basica
            print("1. Informacion de la conexion:")
            result = conn.execute(text("SELECT current_database(), current_user, version();"))
            db_name, db_user, version = result.fetchone()
            print(f"   - Base de datos: {db_name}")
            print(f"   - Usuario: {db_user}")
            print(f"   - Version: {version[:50]}...")

            # Prueba 2: Fecha y hora
            print("\n2. Fecha y hora del servidor:")
            result = conn.execute(text("SELECT now();"))
            server_time = result.fetchone()[0]
            print(f"   - Hora del servidor: {server_time}")

            # Prueba 3: Listar tablas
            print("\n3. Tablas en la base de datos:")
            result = conn.execute(text("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name;
            """))
            tables = result.fetchall()
            if tables:
                for schema, table in tables:
                    print(f"   - {schema}.{table}")
            else:
                print("   - (ninguna tabla)")

            # Prueba 4: Estadisticas
            print("\n4. Estadisticas de la base de datos:")
            result = conn.execute(text("""
                SELECT
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    (SELECT count(*) FROM pg_stat_activity) as active_connections;
            """))
            db_size, active_conns = result.fetchone()
            print(f"   - Tamaño de la base de datos: {db_size}")
            print(f"   - Conexiones activas: {active_conns}")

        print(f"\n{'='*60}")
        print("[OK] Todas las pruebas con SQLAlchemy completadas exitosamente!")
        print(f"{'='*60}\n")
        return True

    except SQLAlchemyError as e:
        print(f"[ERROR] Error de SQLAlchemy: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return False


def main():
    """Funcion principal."""
    print("\n" + "="*60)
    print("PRUEBA DE CONEXION A POSTGRESQL CON SQLALCHEMY")
    print("="*60)

    # URL de conexion desde el host (puerto mapeado)
    database_url_host = "postgresql+psycopg2://devuser:devpass@localhost:15432/aiutox_erp_dev"

    # URL de conexion desde Docker
    database_url_docker = "postgresql+psycopg2://devuser:devpass@db:5432/aiutox_erp_dev"

    # Probar conexion desde el host
    print("\n>>> PRUEBA: Conexion desde el HOST (localhost:15432)")
    success = test_sqlalchemy_connection(database_url_host)

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    print(f"Conexion con SQLAlchemy: {'[OK] EXITOSA' if success else '[ERROR] FALLIDA'}")
    print("="*60 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

