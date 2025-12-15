"""
Test script for session database operations.

Verifies session creation and retrieval using SessionService.
Run: python -m test_session_db
"""

import asyncio
from uuid import UUID

from backend.boundary.db.connection import get_async_session_factory
from backend.application.services.session_service import SessionService


async def test_session_operations():
    """Test session create and read operations."""
    print("=" * 50)
    print("Testing Session Database Operations")
    print("=" * 50)

    SessionFactory = get_async_session_factory()

    async with SessionFactory() as db:
        try:
            session_service = SessionService(db=db)

            # Test 1: Create a session
            print("\n[TEST 1] Creating session...")
            metadata = {"test": True, "name": "Test Session"}
            session_id = await session_service.create_session(metadata=metadata)
            print(f"  Created session ID: {session_id}")

            # Commit the transaction
            await db.commit()
            print("  Transaction committed")

            # Test 2: Read the session back
            print("\n[TEST 2] Reading session back...")
            session_data = await session_service.get_session(session_id)
            print(f"  Session data: {session_data}")

            # Test 3: List all sessions
            print("\n[TEST 3] Listing all sessions...")
            all_sessions = await session_service.get_all_sessions(limit=10)
            print(f"  Total sessions found: {len(all_sessions)}")
            for s in all_sessions:
                print(f"    - {s['id']}: {s.get('metadata', {})}")

            # Test 4: Try to read a non-existent session
            print("\n[TEST 4] Testing non-existent session...")
            fake_id = UUID("00000000-0000-0000-0000-000000000000")
            try:
                await session_service.get_session(fake_id)
                print("  ERROR: Should have raised ValueError")
            except ValueError as e:
                print(f"  Correctly raised ValueError: {e}")

            print("\n" + "=" * 50)
            print("All tests passed!")
            print("=" * 50)

            return session_id

        except Exception as e:
            await db.rollback()
            print(f"\nERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise


async def test_session_persistence():
    """Test that sessions persist across database sessions."""
    print("\n" + "=" * 50)
    print("Testing Session Persistence Across DB Sessions")
    print("=" * 50)

    SessionFactory = get_async_session_factory()

    # Create session in first DB session
    async with SessionFactory() as db:
        session_service = SessionService(db=db)
        print("\n[STEP 1] Creating session in first DB connection...")
        session_id = await session_service.create_session(metadata={"persistence_test": True})
        print(f"  Created session ID: {session_id}")
        await db.commit()
        print("  Committed")

    # Read session in a NEW DB session
    async with SessionFactory() as db:
        session_service = SessionService(db=db)
        print("\n[STEP 2] Reading session in NEW DB connection...")
        try:
            session_data = await session_service.get_session(session_id)
            print(f"  SUCCESS! Session found: {session_data}")
        except ValueError as e:
            print(f"  FAILED! Session not found: {e}")
            print("  This means sessions are NOT being persisted!")
            return False

    print("\n" + "=" * 50)
    print("Persistence test passed!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    print("Starting session database tests...\n")

    try:
        # Run basic operations test
        asyncio.run(test_session_operations())

        # Run persistence test
        asyncio.run(test_session_persistence())

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        exit(1)
