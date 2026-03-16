import hashlib
import logging
import mysql.connector
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

_SKIP_LOG_INTERVAL = 1000  # log a summary every N skipped rows, not every row


def hash_quote(text: str) -> str:
    """SHA-256 hash of stripped quote text for deduplication."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def import_csv(
    filepath: str,
    conn: mysql.connector.MySQLConnection,
    batch_size: int = 2000,
) -> dict:
    """
    Import quotes from CSV idempotently using pandas for fast parsing.
    Malformed rows are skipped and logged. Running twice is safe.
    Returns stats: inserted / skipped / errors.
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

    logger.info(f"Starting CSV import: {filepath}")

    try:
        chunks = pd.read_csv(
            filepath,
            chunksize=batch_size,
            dtype=str,              # read all columns as str — avoids type coercion issues
            keep_default_na=False,  # prevent pandas turning blanks into NaN
            on_bad_lines="skip",    # skip malformed rows silently (pandas logs them)
            encoding="utf-8",
            encoding_errors="replace",
        )
    except Exception as e:
        logger.error(f"Failed to open CSV: {e}")
        raise

    for chunk_num, chunk in enumerate(chunks, start=1):
        # Normalise column names: strip whitespace and lowercase
        chunk.columns = [c.lower().strip() for c in chunk.columns]

        if "quote" not in chunk.columns:
            logger.error("CSV is missing required 'quote' column. Aborting import.")
            raise ValueError("CSV missing required 'quote' column.")

        batch = []
        for _, row in chunk.iterrows():
            try:
                quote_text = row.get("quote", "").strip()
                if not quote_text or len(quote_text) < 5:
                    stats["errors"] += 1
                    logger.debug(f"Chunk {chunk_num}: skipping row — quote too short or empty.")
                    continue

                author = (row.get("author") or "Unknown").strip()[:255]
                category = (row.get("category") or "").strip()[:255]
                q_hash = hash_quote(quote_text)
                batch.append((quote_text, author, category, q_hash))

            except Exception as e:
                stats["errors"] += 1
                logger.warning(f"Chunk {chunk_num}: skipping malformed row — {e}")
                continue

        if batch:
            cursor.executemany(sql, batch)
            inserted = cursor.rowcount
            skipped = len(batch) - inserted
            stats["inserted"] += inserted
            stats["skipped"] += skipped
            conn.commit()
            logger.info(
                f"Chunk {chunk_num}: {inserted} inserted, {skipped} duplicates skipped."
            )

    cursor.close()
    logger.info(
        f"Import complete — inserted: {stats['inserted']}, "
        f"skipped: {stats['skipped']}, errors: {stats['errors']}"
    )
    return stats