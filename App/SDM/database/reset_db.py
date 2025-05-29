"""
Script to reset the database by dropping and recreating all tables.
"""

from connection import db
from schema import CREATE_TABLES
import psycopg2

def reset_database():
    """Drop all existing tables and recreate them."""
    try:
        # Drop all existing tables
        drop_tables = """
        DROP TABLE IF EXISTS user_study_access CASCADE;
        DROP TABLE IF EXISTS sdm_instances CASCADE;
        DROP TABLE IF EXISTS studies CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        """
        
        print("Dropping existing tables...")
        with db.get_cursor() as cursor:
            cursor.execute(drop_tables)
        print("Tables dropped successfully.")
        
        # Create new tables
        print("Creating new tables...")
        with db.get_cursor() as cursor:
            cursor.execute(CREATE_TABLES)
        print("Tables created successfully.")
        
        print("Database reset complete!")
        
    except psycopg2.OperationalError as e:
        print(f"Database connection error: {str(e)}")
        print("Please check your database configuration in .env file")
        raise
    except Exception as e:
        print(f"Error resetting database: {str(e)}")
        raise

if __name__ == "__main__":
    reset_database() 