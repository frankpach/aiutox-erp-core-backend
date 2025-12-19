#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para probar la conexión a PostgreSQL desde Python."""

import sys
import os
from datetime import datetime

# Configurar codificación UTF-8 para Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("ERROR: psycopg2 no está instalado.")
    print("Instálalo con: pip install psycopg2-binary")
    sys.exit(1)


def test_connection(host, port, database, user, password):
    """Prueba la conexión a PostgreSQL."""
    print(f"\n{'='*60}")
    print(f"Probando conexión a PostgreSQL")
    print(f"{'='*60}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"{'='*60}\n")

    try:
        # Intentar conexión
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            connect_timeout=5
        )

        print("[OK] Conexion exitosa!\n")

        # Crear cursor
        cur = conn.cursor()

        # Prueba 1: Información de la conexión
        print("1. Información de la conexión:")
        cur.execute("SELECT current_database(), current_user, version();")
        db_name, db_user, version = cur.fetchone()
        print(f"   - Base de datos: {db_name}")
        print(f"   - Usuario: {db_user}")
        print(f"   - Versión: {version[:50]}...")

        # Prueba 2: Fecha y hora del servidor
        print("\n2. Fecha y hora del servidor:")
        cur.execute("SELECT now(), timezone('UTC', now());")
        server_time, utc_time = cur.fetchone()
        print(f"   - Hora del servidor: {server_time}")
        print(f"   - Hora UTC: {utc_time}")

        # Prueba 3: Listar bases de datos
        print("\n3. Bases de datos disponibles:")
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;")
        databases = cur.fetchall()
        for db in databases:
            print(f"   - {db[0]}")

        # Prueba 4: Listar esquemas
        print("\n4. Esquemas en la base de datos:")
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast') ORDER BY schema_name;")
        schemas = cur.fetchall()
        if schemas:
            for schema in schemas:
                print(f"   - {schema[0]}")
        else:
            print("   - (ningún esquema personalizado)")

        # Prueba 5: Listar tablas
        print("\n5. Tablas en la base de datos:")
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name;
        """)
        tables = cur.fetchall()
        if tables:
            for schema, table in tables:
                print(f"   - {schema}.{table}")
        else:
            print("   - (ninguna tabla)")

        # Prueba 6: Información de la conexión
        print("\n6. Información de la conexión:")
        cur.execute("SELECT inet_server_addr(), inet_server_port(), inet_client_addr();")
        server_addr, server_port, client_addr = cur.fetchone()
        print(f"   - Dirección del servidor: {server_addr or 'N/A'}")
        print(f"   - Puerto del servidor: {server_port or 'N/A'}")
        print(f"   - Dirección del cliente: {client_addr or 'N/A'}")

        # Prueba 7: Estadísticas de la base de datos
        print("\n7. Estadísticas de la base de datos:")
        cur.execute("""
            SELECT
                pg_size_pretty(pg_database_size(current_database())) as db_size,
                (SELECT count(*) FROM pg_stat_activity) as active_connections;
        """)
        db_size, active_conns = cur.fetchone()
        print(f"   - Tamaño de la base de datos: {db_size}")
        print(f"   - Conexiones activas: {active_conns}")

        # Cerrar cursor y conexión
        cur.close()
        conn.close()

        print(f"\n{'='*60}")
        print("[OK] Todas las pruebas completadas exitosamente!")
        print(f"{'='*60}\n")
        return True

    except psycopg2.OperationalError as e:
        print(f"[ERROR] Error de conexion: {e}")
        return False
    except psycopg2.Error as e:
        print(f"[ERROR] Error de PostgreSQL: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        return False


def main():
    """Función principal."""
    print("\n" + "="*60)
    print("PRUEBA DE CONEXIÓN A POSTGRESQL DESDE PYTHON")
    print("="*60)

    # Configuración para conexión desde el host (puerto mapeado)
    config_host = {
        "host": "localhost",
        "port": 15432,
        "database": "aiutox_erp_dev",
        "user": "devuser",
        "password": "devpass"
    }

    # Configuración para conexión desde dentro de Docker
    config_docker = {
        "host": "db",
        "port": 5432,
        "database": "aiutox_erp_dev",
        "user": "devuser",
        "password": "devpass"
    }

    # Probar conexión desde el host
    print("\n>>> PRUEBA 1: Conexión desde el HOST (localhost:15432)")
    success_host = test_connection(**config_host)

    # Probar conexión desde Docker (si estamos dentro de un contenedor)
    print("\n>>> PRUEBA 2: Conexión desde DOCKER (db:5432)")
    print("(Esta prueba solo funcionará si se ejecuta dentro de un contenedor Docker)")
    try:
        success_docker = test_connection(**config_docker)
    except Exception as e:
        print(f"   (Omitida - no estamos en Docker: {e})")
        success_docker = None

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    print(f"Conexion desde host: {'[OK] EXITOSA' if success_host else '[ERROR] FALLIDA'}")
    if success_docker is not None:
        print(f"Conexion desde Docker: {'[OK] EXITOSA' if success_docker else '[ERROR] FALLIDA'}")
    print("="*60 + "\n")

    return 0 if success_host else 1


if __name__ == "__main__":
    sys.exit(main())


