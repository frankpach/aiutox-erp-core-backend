#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script para probar la conexión de la aplicación a la base de datos."""

import sys
import os

# Configurar codificación UTF-8 para Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

print("\n" + "="*60)
print("PRUEBA DE CONEXION DE LA APLICACION A LA BASE DE DATOS")
print("="*60)

# Probar con configuración para desarrollo local (fuera de Docker)
print("\n>>> Probando con configuración LOCAL (localhost:15432)")
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://devuser:devpass@localhost:15432/aiutox_erp_dev'
os.environ['POSTGRES_HOST'] = 'localhost'
os.environ['POSTGRES_PORT'] = '15432'

# Limpiar cache de settings
from app.core.config_file import get_settings
get_settings.cache_clear()

try:
    from app.core.db.session import engine
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text('SELECT current_database(), current_user, version()'))
        db, user, version = result.fetchone()
        print(f"[OK] Conexion exitosa!")
        print(f"   - Base de datos: {db}")
        print(f"   - Usuario: {user}")
        print(f"   - Version: {version[:50]}...")

        # Probar una consulta más
        result = conn.execute(text('SELECT now()'))
        server_time = result.fetchone()[0]
        print(f"   - Hora del servidor: {server_time}")

    print("\n[OK] La aplicacion puede conectarse correctamente a la base de datos!")
    print("="*60 + "\n")
    sys.exit(0)

except Exception as e:
    print(f"\n[ERROR] Error de conexion: {e}")
    print("\nNOTA: Si estas ejecutando desde fuera de Docker,")
    print("asegurate de que los contenedores esten corriendo:")
    print("  docker-compose -f docker-compose.dev.yml up -d db redis")
    print("="*60 + "\n")
    sys.exit(1)

