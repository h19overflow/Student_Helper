"""Quick test to verify database connection works."""

import sys
from sqlalchemy import text
from backend.boundary.db.connection import get_engine, get_session_factory
from backend.configs import get_settings

def test_connection():
    """Test basic database connectivity."""
    try:
        print("Loading settings...")
        settings = get_settings()
        print(f"Database URL: {settings.database.database_url}")

        print("\nCreating engine...")
        engine = get_engine()

        print("Testing connection with pool_pre_ping...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✓ Connection successful: {result.fetchone()}")

        print("\nTesting session factory...")
        SessionFactory = get_session_factory()
        session = SessionFactory()

        try:
            result = session.execute(text("SELECT 1"))
            print(f"✓ Session query successful: {result.fetchone()}")
        finally:
            session.close()

        print("\n✓ All connection tests passed!")
        return True

    except Exception as e:
        print(f"\n✗ Connection failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
