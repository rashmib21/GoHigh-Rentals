# ─────────────────────────────────────────────
# db.py  –  Database connection helper
# ─────────────────────────────────────────────
# This file has ONE job: connect to the MySQL
# database and return the connection object.
# If the connection fails, it returns None.
# ─────────────────────────────────────────────

import mysql.connector
import os
from dotenv import load_dotenv

# Load variables from .env file (DB_USER, DB_PASSWORD, etc.)
load_dotenv()


def get_db_connection():
    """
    Try to connect to MySQL using credentials from .env file.
    Returns the connection object if successful, or None if it fails.
    """
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return connection

    except Exception as e:
        print("Database connection error:", e)
        return None