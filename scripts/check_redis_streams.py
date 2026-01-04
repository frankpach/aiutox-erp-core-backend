#!/usr/bin/env python3
"""Script para verificar y limpiar streams de Redis para tests."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config_file import get_settings
from app.core.pubsub.client import RedisStreamsClient

settings = get_settings()


async def check_redis_streams():
    """Verificar y mostrar información de los streams de Redis."""
    client = RedisStreamsClient(redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD)

    try:
        async with client.connection() as redis_client:
            # Listar todos los streams
            stream_keys = await redis_client.keys("events:*")
            print(f"Streams encontrados: {stream_keys}")

            for stream_key in stream_keys:
                print(f"\n{'='*60}")
                print(f"Stream: {stream_key}")
                print(f"{'='*60}")

                # Información del stream
                try:
                    info = await redis_client.xinfo_stream(stream_key)
                    print(f"Longitud: {info.get('length', 0)} mensajes")
                    print(f"Primer ID: {info.get('first-entry', 'N/A')}")
                    print(f"Último ID: {info.get('last-entry', 'N/A')}")
                except Exception as e:
                    print(f"Error obteniendo info: {e}")

                # Ver últimos 10 mensajes
                try:
                    messages = await redis_client.xrange(stream_key, count=10)
                    print(f"\nÚltimos {len(messages)} mensajes:")
                    for msg_id, data in messages:
                        metadata_source = data.get('metadata_source', 'NOT FOUND')
                        event_type = data.get('event_type', 'N/A')
                        print(f"  ID: {msg_id}")
                        print(f"    event_type: {event_type}")
                        print(f"    metadata_source: {metadata_source}")
                        if metadata_source == 'NOT FOUND' or metadata_source == '':
                            print(f"    ⚠️  PROBLEMA: metadata_source faltante o vacío!")
                            print(f"    Datos completos: {data}")
                except Exception as e:
                    print(f"Error leyendo mensajes: {e}")

                # Ver grupos de consumidores
                try:
                    groups = await redis_client.xinfo_groups(stream_key)
                    if groups:
                        print(f"\nGrupos de consumidores: {len(groups)}")
                        for group in groups:
                            print(f"  - {group.get('name', 'N/A')}: {group.get('consumers', 0)} consumidores")
                except Exception as e:
                    print(f"Error obteniendo grupos: {e}")

    finally:
        await client.close()


async def clean_test_streams():
    """Limpiar streams de test."""
    client = RedisStreamsClient(redis_url=settings.REDIS_URL, password=settings.REDIS_PASSWORD)

    try:
        async with client.connection() as redis_client:
            streams_to_clean = [
                settings.REDIS_STREAM_DOMAIN,
                settings.REDIS_STREAM_TECHNICAL,
                settings.REDIS_STREAM_FAILED,
            ]

            for stream_key in streams_to_clean:
                try:
                    # Verificar si existe
                    length = await redis_client.xlen(stream_key)
                    if length > 0:
                        print(f"Limpiando stream {stream_key} ({length} mensajes)...")
                        # Eliminar todos los mensajes
                        messages = await redis_client.xrange(stream_key, count=10000)
                        if messages:
                            for msg_id, _ in messages:
                                await redis_client.xdel(stream_key, msg_id)
                        print(f"✅ Stream {stream_key} limpiado")
                    else:
                        print(f"Stream {stream_key} ya está vacío")
                except Exception as e:
                    print(f"Error limpiando {stream_key}: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        print("Limpiando streams de test...")
        asyncio.run(clean_test_streams())
    else:
        print("Verificando streams de Redis...")
        asyncio.run(check_redis_streams())
        print("\n💡 Para limpiar los streams, ejecuta: python scripts/check_redis_streams.py clean")




















