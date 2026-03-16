import logging
import mysql.connector
from mysql.connector import Error
from typing import Optional
import config

logger = logging.getLogger(__name__)


def get_connection(
    host: str = config.DB_HOST,
    user: str = config.DB_USER,
    password: str = config.DB_PASSWORD,
    database: str = config.DB_NAME,
) -> Optional[mysql.connector.MySQLConnection]:
    """Create and return a MySQL connection, or None on failure."""
    try:
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            connection_timeout=5,
        )
        logger.info("Database connection established.")
        return conn
    except Error as e:
        logger.error(f"Cannot connect to database: {e}")
        print(f"[DB ERROR] Cannot connect to database: {e}")
        return None


def ensure_schema(conn: mysql.connector.MySQLConnection) -> None:
    """Create tables and indexes if they don't exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            quote       TEXT NOT NULL,
            author      VARCHAR(255),
            category    VARCHAR(255),
            quote_hash  CHAR(64) UNIQUE NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_author (author),
            FULLTEXT INDEX idx_quote_fulltext (quote, category)
        ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """)
    conn.commit()
    cursor.close()
    logger.info("Schema verified.")