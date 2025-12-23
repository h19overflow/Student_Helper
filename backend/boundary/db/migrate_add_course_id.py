"""
Migration script to add course_id column to sessions table.

This script adds the missing course_id foreign key column to the existing
sessions table without losing any data. Safe to run multiple times (idempotent).

Usage:
    python -m backend.boundary.db.migrate_add_course_id
"""

from sqlalchemy import text, create_engine

from backend.configs import get_settings


def add_course_id_column() -> None:
    """
    Add course_id column to sessions table if it doesn't exist.

    This migration:
    1. Checks if the column already exists
    2. If not, adds course_id as UUID FK with ON DELETE SET NULL
    3. Makes the column nullable (for backward compatibility)
    """
    settings = get_settings()
    db_config = settings.database

    # Create sync engine
    engine = create_engine(
        db_config.database_url,
        echo=False,
    )

    with engine.begin() as conn:
        # Check if column exists
        check_column_sql = text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sessions'
                AND column_name = 'course_id'
            )
        """)
        result = conn.execute(check_column_sql)
        column_exists = result.scalar()

        if column_exists:
            print("✅ Column 'course_id' already exists in 'sessions' table")
            return

        # Column doesn't exist, add it
        print("Adding 'course_id' column to 'sessions' table...")

        # Add the column
        add_column_sql = text("""
            ALTER TABLE sessions
            ADD COLUMN course_id UUID NULL,
            ADD CONSTRAINT fk_sessions_course_id
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL
        """)

        try:
            conn.execute(add_column_sql)
            conn.commit()
            print("✅ Column 'course_id' added successfully to 'sessions' table")
            print("✅ Foreign key constraint created")
        except Exception as e:
            print(f"❌ Failed to add column: {e}")
            raise


if __name__ == "__main__":
    add_course_id_column()
