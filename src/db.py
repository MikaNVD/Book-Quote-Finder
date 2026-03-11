import logging
import mysql.connector
from mysql.connector import Error
from typing import Optional

logger = logging.getLogger(__name__)

# Default connection settings; override via get_connection() or CLI args.
DEFAULT_HOST = "localhost"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = ""
DEFAULT_DATABASE = "book_quotes"


def get_connection(
    host: str = DEFAULT_HOST,
    user: str = DEFAULT_USER,
    password: str = DEFAULT_PASSWORD,
    database: str = DEFAULT_DATABASE,
) -> Optional[mysql.connector.MySQLConnection]:
    """Create and return a MySQL connection, or None on failure."""
    try:
        return mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            connection_timeout=5,
        )
    except Error as e:
        logger.error("Cannot connect to database: %s", e)
        return None


def ensure_schema(conn: mysql.connector.MySQLConnection) -> None:
    """Create tables if they don't exist."""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                quote TEXT NOT NULL,
                author VARCHAR(255),
                category VARCHAR(255),
                quote_hash CHAR(64) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_author (author),
                FULLTEXT INDEX idx_quote_fulltext (quote, category)
            ) ENGINE=InnoDB CHARACTER SET utf8mb4
        """)
    conn.commit()