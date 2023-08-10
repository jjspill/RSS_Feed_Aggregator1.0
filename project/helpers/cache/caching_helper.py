import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILEPATH = os.path.join(BASE_DIR, "cache.db")

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS cache (
        url TEXT PRIMARY KEY,
        last_seen_id TEXT,
        etag TEXT,
        last_modified TEXT
    );
"""


def setup_database():
    # Check if database file exists
    if not os.path.exists(DATABASE_FILEPATH):
        # Create database
        with sqlite3.connect(DATABASE_FILEPATH) as conn:
            cursor = conn.cursor()

            # Table setup
            try:
                cursor.execute(CREATE_TABLE_SQL)
            except sqlite3.Error as e:
                print(f"Error: {e}")

            print("==== Database set up complete")
    else:
        print("==== Database exists")


def update_cache(url, last_seen_id, etag=None, last_modified=None):
    # Connect to database
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        cursor = conn.cursor()

        # Insert or update cache entry
        cursor.execute(
            """
            INSERT OR REPLACE INTO cache (url, last_seen_id, etag, last_modified)
            VALUES (?, ?, ?, ?)
            """,
            (url, last_seen_id, etag, last_modified),
        )


def fetch_cache(url):
    # Connect to database
    with sqlite3.connect(DATABASE_FILEPATH) as conn:
        cursor = conn.cursor()

        # Fetch cache entry
        cursor.execute(
            "SELECT last_seen_id, etag, last_modified FROM cache WHERE url=?",
            (url,),
        )
        result = cursor.fetchone()

    return None if result is None else result
