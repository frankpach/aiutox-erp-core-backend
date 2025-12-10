"""Simple script to test database connection and diagnose encoding issues."""

import sys
from urllib.parse import quote_plus

try:
    from app.core.config import get_settings

    print("Loading settings...")
    settings = get_settings()

    print(f"POSTGRES_HOST: {settings.POSTGRES_HOST}")
    print(f"POSTGRES_PORT: {settings.POSTGRES_PORT}")
    print(f"POSTGRES_USER: {settings.POSTGRES_USER}")
    print(f"POSTGRES_PASSWORD length: {len(settings.POSTGRES_PASSWORD)}")
    print(f"POSTGRES_PASSWORD (first 10 chars): {settings.POSTGRES_PASSWORD[:10]}...")
    print(f"POSTGRES_DB: {settings.POSTGRES_DB}")

    # Test password encoding
    encoded_password = quote_plus(settings.POSTGRES_PASSWORD)
    print(f"\nEncoded password length: {len(encoded_password)}")
    print(f"Encoded password (first 20 chars): {encoded_password[:20]}...")

    # Build URL
    database_url = (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{encoded_password}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    print(f"\nDATABASE_URL length: {len(database_url)}")
    print(f"DATABASE_URL (without password): {database_url.split('@')[0].split(':')[0]}://***:***@{database_url.split('@')[1]}")

    # Try to create engine
    print("\nAttempting to create SQLAlchemy engine...")
    from sqlalchemy import create_engine

    engine = create_engine(
        database_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

    print("Engine created successfully!")

    # Try to connect
    print("\nAttempting to connect to database...")
    with engine.connect() as conn:
        result = conn.execute("SELECT version();")
        version = result.fetchone()[0]
        print(f"✅ Connection successful!")
        print(f"PostgreSQL version: {version}")

        # Check if database exists
        result = conn.execute("SELECT current_database();")
        db_name = result.fetchone()[0]
        print(f"Current database: {db_name}")

except UnicodeDecodeError as e:
    print(f"\n❌ UnicodeDecodeError: {e}")
    print("This usually means the password contains special characters.")
    print("Try encoding the password in the .env file or use only ASCII characters.")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
