import csv
import hashlib
import mysql.connector
from typing import Optional
from pathlib import Path


def hash_quote(text: str) -> str:
    """Generate a SHA-256 hash for deduplication."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def import_csv(
    filepath: str,
    conn: mysql.connector.MySQLConnection,
    batch_size: int = 500
) -> dict:
    """
    Import quotes from CSV into MySQL idempotently.
    Returns stats dict with inserted/skipped/error counts.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {filepath}")

    stats = {"inserted": 0, "skipped": 0, "errors": 0}
    cursor = conn.cursor()

    sql = """
        INSERT IGNORE INTO quotes (quote, author, category, quote_hash)
        VALUES (%s, %s, %s, %s)
    """

    batch = []
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for line_num, row in enumerate(reader, start=2):
            try:
                # Handle malformed rows — check required field exists
                quote_text = row.get("quote", "").strip()
                if not quote_text or len(quote_text) < 5:
                    stats["errors"] += 1
                    continue

                author = (row.get("author") or "Unknown").strip()[:255]
                category = (row.get("category") or "").strip()[:255]
                q_hash = hash_quote(quote_text)

                batch.append((quote_text, author, category, q_hash))

                if len(batch) >= batch_size:
                    result = cursor.executemany(sql, batch)
                    stats["inserted"] += cursor.rowcount
                    stats["skipped"] += len(batch) - cursor.rowcount
                    conn.commit()
                    batch = []

            except Exception as e:
                stats["errors"] += 1
                print(f"[WARN] Skipping row {line_num}: {e}")
                continue

    # Final batch
    if batch:
        cursor.executemany(sql, batch)
        stats["inserted"] += cursor.rowcount
        stats["skipped"] += len(batch) - cursor.rowcount
        conn.commit()

    cursor.close()
    return stats