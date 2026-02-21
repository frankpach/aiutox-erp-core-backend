#!/usr/bin/env python3
"""
Script para probar la conexión a Redis en GitHub Actions
"""
import os
import sys

import redis
from redis.exceptions import ConnectionError


def test_redis_connection():
    """Test Redis connection using environment variables"""

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    print("🔗 Testing Redis connection...")

    try:
        # Parse connection string and test connection
        client = redis.from_url(redis_url)

        # Test ping
        result = client.ping()

        if result:
            print("✅ Redis connection successful!")

            # Test basic operations
            test_key = "test:github:actions"
            client.set(test_key, "working")
            value = client.get(test_key)

            print(f"📈 Redis SET/GET test: {value.decode() if value else 'None'}")

            # Cleanup
            client.delete(test_key)

            # Test info
            info = client.info()
            print(f"📊 Redis version: {info.get('redis_version', 'unknown')}")
            print(f"📊 Redis used memory: {info.get('used_memory_human', 'unknown')}")

            client.close()

            print("✅ All Redis operations completed successfully!")
            return True
        else:
            print("❌ Redis ping failed")
            return False

    except ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_redis_connection()
    sys.exit(0 if success else 1)
