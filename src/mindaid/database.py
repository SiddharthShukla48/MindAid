"""
Database configuration and connection management
"""

import sqlite3
import os
from pathlib import Path

DATABASE_PATH = Path("database.db")

def init_db():
    """Initialize database and create tables if they don't exist"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            date TEXT,
            firstname TEXT,
            lastname TEXT,
            email TEXT,
            disorder TEXT DEFAULT 'Not-Diagnosed',
            severity TEXT DEFAULT 'Not-Diagnosed',
            history TEXT DEFAULT ''
        )
    """)

    # Create doctors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            firstname TEXT,
            lastname TEXT,
            fees TEXT,
            qualification TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    return sqlite3.connect(DATABASE_PATH)

def close_db(conn):
    """Close database connection"""
    if conn:
        conn.close()
