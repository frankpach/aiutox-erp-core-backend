"""Script simple para verificar que los tests de pubsub pueden ejecutarse sin colgarse."""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

async def test_redis_connection():
    """Test simple de conexión a Redis."""
    try:
        from app.core.config_file import get_settings
        from app.core.pubsub.client import RedisStreamsClient

        settings = get_settings()
        print(f"Intentando conectar a Redis: {settings.REDIS_URL}")

        client = RedisStreamsClient(
            redis_url=settings.REDIS_URL,
            password=settings.REDIS_PASSWORD
        )

        # Intentar conectar con timeout
        try:
            async with asyncio.wait_for(client.connection(), timeout=3.0):
                async with client.connection() as conn:
                    result = await conn.ping()
                    print(f"✅ Redis está disponible: {result}")
                    await client.close()
                    return True
        except asyncio.TimeoutError:
            print("❌ Timeout al conectar a Redis")
            return False
        except Exception as e:
            print(f"❌ Error al conectar a Redis: {e}")
            return False
    except Exception as e:
        print(f"❌ Error al importar módulos: {e}")
        return False

def test_imports():
    """Test que todos los módulos se pueden importar."""
    try:
        print("Verificando imports...")
        from app.core.pubsub import (
            RedisStreamsClient,
            EventPublisher,
            EventConsumer,
            Event,
            EventMetadata,
        )
        print("✅ Todos los imports funcionan correctamente")
        return True
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Diagnóstico de Pub-Sub Module")
    print("=" * 60)

    # Test imports
    imports_ok = test_imports()

    if imports_ok:
        # Test Redis connection
        print("\n" + "=" * 60)
        redis_ok = asyncio.run(test_redis_connection())

        if redis_ok:
            print("\n✅ Todo está funcionando correctamente")
            sys.exit(0)
        else:
            print("\n⚠️  Redis no está disponible, pero los tests unitarios deberían funcionar")
            sys.exit(0)
    else:
        print("\n❌ Hay problemas con los imports")
        sys.exit(1)


