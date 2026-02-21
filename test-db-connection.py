#!/usr/bin/env python3
"""
Script para probar la conexión a la base de datos en GitHub Actions
"""
import os
import sys

import psycopg2
from psycopg2 import OperationalError


def test_connection():
    """Test database connection using environment variables"""

    # Try TEST_DATABASE_URL first, then DATABASE_URL
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")

    if not db_url:
        print("❌ ERROR: Neither TEST_DATABASE_URL nor DATABASE_URL is set")
        return False

    print("🔗 Testing connection to database")

    try:
        # Parse connection string and test connection
        conn = psycopg2.connect(db_url)

        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        print("✅ Database connection successful!")
        print(f"📊 PostgreSQL version: {version[0]}")

        # Test if we can create a table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Test insert
        cursor.execute("INSERT INTO test_table DEFAULT VALUES;")
        conn.commit()

        # Test select
        cursor.execute("SELECT COUNT(*) FROM test_table;")
        count = cursor.fetchone()[0]
        print(f"📈 Test table records: {count}")

        # Cleanup
        cursor.execute("DROP TABLE IF EXISTS test_table;")
        conn.commit()

        cursor.close()
        conn.close()

        print("✅ All database operations completed successfully!")
        return True

    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
