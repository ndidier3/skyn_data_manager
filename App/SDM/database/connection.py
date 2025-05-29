"""
Database connection management for SDM web interface.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

class DatabaseConnection:
    def __init__(self):
        self.db_params = {
            'dbname': os.getenv('SDM_DB_NAME', 'sdm_db'),
            'user': os.getenv('SDM_DB_USER', 'sdm_user'),
            'password': os.getenv('SDM_DB_PASSWORD', ''),
            'host': os.getenv('SDM_DB_HOST', 'localhost'),
            'port': os.getenv('SDM_DB_PORT', '5432')
        }

    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_params, cursor_factory=RealDictCursor)
            yield conn
        finally:
            if conn is not None:
                conn.close()

    @contextmanager
    def get_cursor(self):
        """Get a database cursor with automatic cleanup."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute_query(self, query, params=None):
        """Execute a query and return all results."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    def execute_single(self, query, params=None):
        """Execute a query and return a single result."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()

    def execute_update(self, query, params=None):
        """Execute an update query and return the number of affected rows."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.rowcount

# Create a global database connection instance
db = DatabaseConnection() 