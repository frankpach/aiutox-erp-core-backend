"""Script interactivo para verificar conexión a Redis."""

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


async def test_redis_connection():
    """Test interactivo de conexión a Redis."""
    print("=" * 70)
    print("[VERIFICACION] Verificacion de Conexion a Redis")
    print("=" * 70)
    print()

    try:
        from app.core.config_file import get_settings
        from app.core.pubsub.client import RedisStreamsClient

        settings = get_settings()

        print("[CONFIG] Configuracion actual:")
        print(f"   REDIS_URL: {settings.REDIS_URL}")
        print(f"   REDIS_PASSWORD: {'***' if settings.REDIS_PASSWORD else '(vacío)'}")
        print(f"   REDIS_STREAM_DOMAIN: {settings.REDIS_STREAM_DOMAIN}")
        print(f"   REDIS_STREAM_TECHNICAL: {settings.REDIS_STREAM_TECHNICAL}")
        print(f"   REDIS_STREAM_FAILED: {settings.REDIS_STREAM_FAILED}")
        print()

        print("[CONEXION] Intentando conectar a Redis...")
        client = RedisStreamsClient(
            redis_url=settings.REDIS_URL,
            password=settings.REDIS_PASSWORD
        )

        try:
            # Intentar conectar con timeout
            print("   [INFO] Esperando respuesta (timeout: 5 segundos)...")
            redis_conn = await asyncio.wait_for(client._get_client(), timeout=5.0)

            # Hacer ping
            result = await asyncio.wait_for(redis_conn.ping(), timeout=2.0)

            if result:
                print("   [OK] ¡Conexion exitosa!")
                print()

                # Obtener información del servidor
                print("[INFO] Informacion del servidor Redis:")
                try:
                    info = await redis_conn.info()
                    print(f"   Versión: {info.get('redis_version', 'N/A')}")
                    print(f"   Modo: {info.get('redis_mode', 'N/A')}")
                    print(f"   Uptime (días): {info.get('uptime_in_days', 'N/A')}")
                    print(f"   Memoria usada: {info.get('used_memory_human', 'N/A')}")
                    print(f"   Clientes conectados: {info.get('connected_clients', 'N/A')}")
                except Exception as e:
                    print(f"   [WARN] No se pudo obtener info del servidor: {e}")

                print()

                # Verificar streams
                print("[STREAMS] Verificando streams...")
                streams_to_check = [
                    settings.REDIS_STREAM_DOMAIN,
                    settings.REDIS_STREAM_TECHNICAL,
                    settings.REDIS_STREAM_FAILED,
                ]

                for stream_name in streams_to_check:
                    try:
                        stream_info = await redis_conn.xinfo_stream(stream_name)
                        length = stream_info.get("length", 0)
                        print(f"   [OK] {stream_name}: {length} mensajes")
                    except Exception:
                        print(f"   [WARN] {stream_name}: No existe (se creara automaticamente)")

                print()
                print("=" * 70)
                print("[OK] Redis esta configurado correctamente y funcionando")
                print("=" * 70)

                await client.close()
                return True
            else:
                print("   [ERROR] Ping fallo")
                await client.close()
                return False

        except asyncio.TimeoutError:
            print("   [ERROR] Timeout: Redis no respondio en el tiempo esperado")
            print()
            print("[AYUDA] Posibles causas:")
            print("   - Redis no está corriendo")
            print("   - La URL de conexión es incorrecta")
            print("   - Hay un firewall bloqueando la conexión")
            print("   - Redis está en otro puerto")
            try:
                await client.close()
            except Exception:
                pass
            return False

        except ConnectionRefusedError:
            print("   [ERROR] Conexion rechazada: Redis no esta escuchando en esa direccion/puerto")
            print()
            print("[AYUDA] Verifica:")
            print("   - Que Redis esté corriendo: redis-cli ping")
            print("   - Que el puerto sea correcto (por defecto: 6379)")
            print("   - Que no haya un firewall bloqueando")
            try:
                await client.close()
            except Exception:
                pass
            return False

        except Exception as e:
            print(f"   [ERROR] Error de conexion: {type(e).__name__}: {e}")
            print()
            print("[AYUDA] Verifica la configuracion en tu archivo .env o variables de entorno")
            try:
                await client.close()
            except Exception:
                pass
            return False

    except ImportError as e:
        print(f"[ERROR] Error al importar modulos: {e}")
        print()
        print("[AYUDA] Asegurate de estar en el directorio backend y tener las dependencias instaladas")
        return False
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_publish_event():
    """Test de publicación de un evento de prueba."""
    print()
    print("=" * 70)
    print("[TEST] Test de Publicacion de Evento")
    print("=" * 70)
    print()

    try:
        from app.core.config_file import get_settings
        from app.core.pubsub.publisher import EventPublisher
        from app.core.pubsub.client import RedisStreamsClient
        from app.core.pubsub.models import EventMetadata
        from uuid import uuid4

        settings = get_settings()

        client = RedisStreamsClient(
            redis_url=settings.REDIS_URL,
            password=settings.REDIS_PASSWORD
        )
        publisher = EventPublisher(client=client)

        print("[PUBLICAR] Publicando evento de prueba...")
        message_id = await publisher.publish(
            event_type="test.connection",
            entity_type="test",
            entity_id=uuid4(),
            tenant_id=uuid4(),
            metadata=EventMetadata(source="test_script", version="1.0")
        )

        print(f"   [OK] Evento publicado con ID: {message_id}")

        # Verificar que el evento está en el stream
        async with client.connection() as conn:
            stream_info = await conn.xinfo_stream(settings.REDIS_STREAM_DOMAIN)
            print(f"   [INFO] Stream 'events:domain' ahora tiene {stream_info.get('length', 0)} mensajes")

        await client.close()
        return True

    except Exception as e:
        print(f"   [ERROR] Error al publicar evento: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print()

    # Test de conexión
    connection_ok = asyncio.run(test_redis_connection())

    if connection_ok:
        # Si la conexión funciona, probar publicación
        print()
        respuesta = input("[PREGUNTA] Deseas probar la publicacion de un evento? (s/n): ").strip().lower()
        if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
            publish_ok = asyncio.run(test_publish_event())
        if publish_ok:
            print()
            print("=" * 70)
            print("[OK] Todos los tests pasaron correctamente")
            print("=" * 70)
            sys.exit(0)
        else:
            print()
            print("=" * 70)
            print("[WARN] La conexion funciona pero hay problemas al publicar eventos")
            print("=" * 70)
            sys.exit(1)
    else:
        print()
        print("=" * 70)
        print("[OK] Conexion verificada correctamente")
        print("=" * 70)
        sys.exit(0)
else:
    print()
    print("=" * 70)
    print("[ERROR] No se pudo conectar a Redis")
    print()
    print("[AYUDA] Proximos pasos:")
    print("   1. Verifica que Redis este instalado y corriendo")
    print("   2. Revisa la configuracion en .env o variables de entorno")
    print("   3. Si Redis esta en Docker, verifica que el contenedor este corriendo")
    print("   4. Verifica la URL de conexion (por defecto: redis://localhost:6379/0)")
    print("=" * 70)
    sys.exit(1)

