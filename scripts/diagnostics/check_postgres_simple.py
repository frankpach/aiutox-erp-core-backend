"""Prueba simple para verificar conexión a PostgreSQL - muestra variables y sentencia de conexión."""

import pytest
from urllib.parse import quote_plus

try:
    import psycopg2
    from app.core.config import get_settings
except ImportError:
    pytest.skip("psycopg2 no está instalado", allow_module_level=True)


def test_postgres_connection():
    """Prueba la conexión a PostgreSQL y muestra las variables de conexión."""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DE CONEXIÓN A POSTGRESQL")
    print("=" * 60)

    settings = get_settings()

    # Mostrar todas las variables de conexión
    print(f"\n📋 Variables de conexión:")
    print(f"   POSTGRES_HOST: {settings.POSTGRES_HOST}")
    print(f"   POSTGRES_PORT: {settings.POSTGRES_PORT}")
    print(f"   POSTGRES_USER: {settings.POSTGRES_USER}")
    print(f"   POSTGRES_PASSWORD: {'*' * min(len(settings.POSTGRES_PASSWORD), 20)} (longitud: {len(settings.POSTGRES_PASSWORD)})")
    print(f"   POSTGRES_DB: {settings.POSTGRES_DB}")

    # Construir y mostrar la sentencia de conexión (con contraseña enmascarada)
    password_encoded = quote_plus(str(settings.POSTGRES_PASSWORD), safe="")
    user_encoded = quote_plus(str(settings.POSTGRES_USER), safe="")
    host_encoded = quote_plus(str(settings.POSTGRES_HOST), safe="")
    db_encoded = quote_plus(str(settings.POSTGRES_DB), safe="")

    connection_url = (
        f"postgresql+psycopg2://{user_encoded}:{password_encoded}"
        f"@{host_encoded}:{settings.POSTGRES_PORT}/{db_encoded}"
    )

    # Mostrar URL con contraseña enmascarada
    masked_url = (
        f"postgresql+psycopg2://{user_encoded}:***"
        f"@{host_encoded}:{settings.POSTGRES_PORT}/{db_encoded}"
    )

    print(f"\n🔌 Sentencia de conexión (URL enmascarada):")
    print(f"   {masked_url}")
    print(f"\n🔌 Parámetros de conexión psycopg2.connect():")
    print(f"   host='{settings.POSTGRES_HOST}'")
    print(f"   port={settings.POSTGRES_PORT}")
    print(f"   user='{settings.POSTGRES_USER}'")
    print(f"   password='{'*' * min(len(settings.POSTGRES_PASSWORD), 20)}'")
    print(f"   database='{settings.POSTGRES_DB}'")
    print(f"   connect_timeout=5")

    print(f"\n🔌 Intentando conectar...")

    # Conectar directamente con psycopg2 usando parámetros por nombre
    conn = psycopg2.connect(
        host=str(settings.POSTGRES_HOST),
        port=int(settings.POSTGRES_PORT),
        user=str(settings.POSTGRES_USER),
        password=str(settings.POSTGRES_PASSWORD),
        database=str(settings.POSTGRES_DB),
        connect_timeout=5
    )

    # Ejecutar consultas
    cursor = conn.cursor()

    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]

    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()[0]

    cursor.execute("SELECT current_user;")
    user = cursor.fetchone()[0]

    print(f"\n✅ ¡Conexión exitosa!")
    print(f"   PostgreSQL: {version.split(',')[0]}")
    print(f"   Base de datos: {db_name}")
    print(f"   Usuario: {user}")
    print(f"\n✅ La conexión a PostgreSQL está funcionando correctamente.")

    # Verificar que las consultas funcionaron correctamente
    assert version is not None, "No se pudo obtener la versión de PostgreSQL"
    assert db_name == settings.POSTGRES_DB, f"Base de datos esperada: {settings.POSTGRES_DB}, obtenida: {db_name}"
    assert user == settings.POSTGRES_USER, f"Usuario esperado: {settings.POSTGRES_USER}, obtenido: {user}"

    cursor.close()
    conn.close()

    # Verificar que la conexión se cerró correctamente
    # conn.closed == 0 significa abierta, != 0 significa cerrada
    assert conn.closed != 0, "La conexión debería estar cerrada después de close()"



