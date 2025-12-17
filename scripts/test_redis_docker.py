"""Script para verificar conexión a Redis en Docker."""

import asyncio
import sys
import os
from pathlib import Path

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


async def test_redis_connection_with_password(password: str = ""):
    """Test de conexión a Redis con y sin password."""
    print("=" * 70)
    print("[TEST] Verificacion de Conexion a Redis en Docker")
    print("=" * 70)
    print()

    try:
        from app.core.pubsub.client import RedisStreamsClient

        # Probar sin password primero
        print("[TEST 1] Probando conexion SIN password...")
        try:
            client_no_pass = RedisStreamsClient(
                redis_url="redis://localhost:6379/0",
                password=""
            )
            redis_conn = await asyncio.wait_for(client_no_pass._get_client(), timeout=5.0)
            result = await asyncio.wait_for(redis_conn.ping(), timeout=2.0)

            if result:
                print("   [OK] Conexion exitosa SIN password")
                await client_no_pass.close()

                # Probar operaciones
                print()
                print("[TEST 2] Probando operaciones basicas...")
                client = RedisStreamsClient(
                    redis_url="redis://localhost:6379/0",
                    password=""
                )
                async with client.connection() as conn:
                    # Test de escritura
                    await conn.set("test:connection", "ok")
                    value = await conn.get("test:connection")
                    await conn.delete("test:connection")

                    if value == "ok":
                        print("   [OK] Lectura y escritura funcionan correctamente")

                    # Verificar info del servidor
                    info = await conn.info("server")
                    print(f"   [INFO] Version de Redis: {info.get('redis_version', 'N/A')}")
                    print(f"   [INFO] Modo: {info.get('redis_mode', 'N/A')}")

                await client.close()

                print()
                print("=" * 70)
                print("[OK] Redis esta funcionando correctamente SIN password")
                print("=" * 70)
                print()
                print("[CONFIGURACION] Usa esta configuracion en tu .env:")
                print("   REDIS_URL=redis://localhost:6379/0")
                print("   REDIS_PASSWORD=")
                print()
                return True
            else:
                print("   [ERROR] Ping fallo")
                await client_no_pass.close()
                return False

        except Exception as e:
            print(f"   [ERROR] Error de conexion: {type(e).__name__}: {e}")

            # Si falla sin password, probar con password
            if password:
                print()
                print("[TEST 2] Probando conexion CON password...")
                try:
                    client_with_pass = RedisStreamsClient(
                        redis_url="redis://localhost:6379/0",
                        password=password
                    )
                    redis_conn = await asyncio.wait_for(client_with_pass._get_client(), timeout=5.0)
                    result = await asyncio.wait_for(redis_conn.ping(), timeout=2.0)

                    if result:
                        print("   [OK] Conexion exitosa CON password")
                        await client_with_pass.close()

                        print()
                        print("=" * 70)
                        print("[OK] Redis esta funcionando correctamente CON password")
                        print("=" * 70)
                        print()
                        print("[CONFIGURACION] Usa esta configuracion en tu .env:")
                        print(f"   REDIS_URL=redis://localhost:6379/0")
                        print(f"   REDIS_PASSWORD={password}")
                        print()
                        return True
                    else:
                        print("   [ERROR] Ping fallo con password")
                        await client_with_pass.close()
                        return False
                except Exception as e2:
                    print(f"   [ERROR] Error de conexion con password: {type(e2).__name__}: {e2}")
                    return False
            else:
                return False

    except ImportError as e:
        print(f"[ERROR] Error al importar modulos: {e}")
        print()
        print("[AYUDA] Asegurate de tener las dependencias instaladas:")
        print("   uv sync --extra dev")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()

    # Obtener password de argumentos o variable de entorno
    password = ""
    if len(sys.argv) > 1:
        password = sys.argv[1]
    elif "REDIS_PASSWORD" in os.environ:
        password = os.environ["REDIS_PASSWORD"]

    success = asyncio.run(test_redis_connection_with_password(password))

    if not success:
        print()
        print("=" * 70)
        print("[ERROR] No se pudo conectar a Redis")
        print("=" * 70)
        print()
        print("[AYUDA] Verifica:")
        print("   1. Que el contenedor Docker este corriendo: docker ps")
        print("   2. Que el puerto 6379 este mapeado correctamente")
        print("   3. Que Redis este escuchando en localhost:6379")
        print()
        print("[TEST MANUAL] Prueba manualmente:")
        print("   docker exec <container_id> redis-cli ping")
        sys.exit(1)
    else:
        sys.exit(0)









