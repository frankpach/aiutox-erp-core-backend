"""Script de diagnóstico completo para PostgreSQL en Windows."""

import sys
import subprocess
import socket
from pathlib import Path

# Agregar el directorio backend al path
backend_root = Path(__file__).parent
sys.path.insert(0, str(backend_root))

print("=" * 70)
print("DIAGNÓSTICO DE POSTGRESQL EN WINDOWS")
print("=" * 70)

# 1. Verificar si PostgreSQL está instalado
print("\n1️⃣  Verificando instalación de PostgreSQL...")
try:
    result = subprocess.run(
        ["where", "psql"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        psql_path = result.stdout.strip().split('\n')[0]
        print(f"   ✅ PostgreSQL encontrado en: {psql_path}")

        # Obtener versión
        try:
            version_result = subprocess.run(
                ["psql", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if version_result.returncode == 0:
                print(f"   📌 Versión: {version_result.stdout.strip()}")
        except Exception:
            pass
    else:
        print("   ❌ PostgreSQL (psql) no encontrado en PATH")
        print("   💡 Buscando en ubicaciones comunes...")

        common_paths = [
            r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
            r"C:\Program Files\PostgreSQL\13\bin\psql.exe",
        ]

        found = False
        for path in common_paths:
            if Path(path).exists():
                print(f"   ✅ Encontrado en: {path}")
                found = True
                break

        if not found:
            print("   ❌ PostgreSQL no encontrado en ubicaciones comunes")
            print("   💡 Instala PostgreSQL o agrega la carpeta bin al PATH")
except Exception as e:
    print(f"   ⚠️  Error al verificar instalación: {e}")

# 2. Verificar si el servicio de PostgreSQL está corriendo
print("\n2️⃣  Verificando servicio de PostgreSQL...")
try:
    result = subprocess.run(
        ["sc", "query", "postgresql-x64-16"],
        capture_output=True,
        text=True,
        timeout=5
    )

    # También probar otros nombres comunes
    service_names = [
        "postgresql-x64-16",
        "postgresql-x64-15",
        "postgresql-x64-14",
        "postgresql-x64-13",
        "postgresql",
        "PostgreSQL"
    ]

    service_found = False
    for service_name in service_names:
        result = subprocess.run(
            ["sc", "query", service_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            if "RUNNING" in result.stdout:
                print(f"   ✅ Servicio '{service_name}' está CORRIENDO")
                service_found = True
                break
            elif "STOPPED" in result.stdout:
                print(f"   ⚠️  Servicio '{service_name}' está DETENIDO")
                print(f"   💡 Inicia el servicio con: net start {service_name}")
                service_found = True
                break

    if not service_found:
        print("   ⚠️  No se encontró el servicio de PostgreSQL")
        print("   💡 Verifica que PostgreSQL esté instalado como servicio")

except Exception as e:
    print(f"   ⚠️  Error al verificar servicio: {e}")

# 3. Verificar si el puerto 5432 está abierto
print("\n3️⃣  Verificando puerto 5432...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 5432))
    sock.close()

    if result == 0:
        print("   ✅ Puerto 5432 está ABIERTO y escuchando")
    else:
        print("   ❌ Puerto 5432 está CERRADO o no responde")
        print("   💡 PostgreSQL puede no estar corriendo o usar otro puerto")
except Exception as e:
    print(f"   ⚠️  Error al verificar puerto: {e}")

# 4. Verificar conexión usando psycopg2
print("\n4️⃣  Verificando conexión con psycopg2...")
try:
    import psycopg2

    # Intentar conectar con credenciales por defecto
    test_configs = [
        {"user": "postgres", "password": "pass", "host": "localhost", "port": 5432},
        {"user": "postgres", "password": "postgres", "host": "localhost", "port": 5432},
        {"user": "root", "password": "pass", "host": "localhost", "port": 5432},
    ]

    connected = False
    for config in test_configs:
        try:
            conn = psycopg2.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                connect_timeout=3
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"   ✅ Conexión exitosa con usuario '{config['user']}'")
            print(f"   📌 PostgreSQL: {version.split(',')[0]}")
            cursor.close()
            conn.close()
            connected = True
            break
        except psycopg2.OperationalError as e:
            continue
        except Exception:
            continue

    if not connected:
        print("   ❌ No se pudo conectar con ninguna configuración probada")
        print("   💡 Verifica usuario y contraseña")

except ImportError:
    print("   ⚠️  psycopg2 no está instalado")
    print("   💡 Instala con: uv sync")
except Exception as e:
    print(f"   ⚠️  Error: {e}")

# 5. Verificar configuración del proyecto
print("\n5️⃣  Verificando configuración del proyecto...")
try:
    from app.core.config import get_settings
    settings = get_settings()

    print(f"   📋 Configuración actual:")
    print(f"      Host: {settings.POSTGRES_HOST}")
    print(f"      Port: {settings.POSTGRES_PORT}")
    print(f"      User: {settings.POSTGRES_USER}")
    print(f"      Database: {settings.POSTGRES_DB}")
    print(f"      Password: {'*' * len(str(settings.POSTGRES_PASSWORD)) if settings.POSTGRES_PASSWORD else '(vacía)'}")

except Exception as e:
    print(f"   ⚠️  Error al leer configuración: {e}")

# 6. Verificar Docker (si está usando Docker)
print("\n6️⃣  Verificando Docker...")
try:
    result = subprocess.run(
        ["docker", "--version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print(f"   ✅ Docker instalado: {result.stdout.strip()}")

        # Verificar contenedores de PostgreSQL
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=postgres", "--format", "{{.Names}} - {{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.stdout.strip():
            print(f"   📦 Contenedores PostgreSQL encontrados:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"      - {line.strip()}")
        else:
            print("   ℹ️  No se encontraron contenedores PostgreSQL")
    else:
        print("   ℹ️  Docker no está instalado o no está en PATH")
except Exception:
    print("   ℹ️  Docker no está disponible")

print("\n" + "=" * 70)
print("RESUMEN DEL DIAGNÓSTICO")
print("=" * 70)
print("\n💡 Comandos útiles:")
print("   - Ver servicios: sc query postgresql-x64-16")
print("   - Iniciar servicio: net start postgresql-x64-16")
print("   - Detener servicio: net stop postgresql-x64-16")
print("   - Conectar con psql: psql -U postgres -h localhost")
print("   - Verificar puerto: netstat -an | findstr 5432")
print("\n")



