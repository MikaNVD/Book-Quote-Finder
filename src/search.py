import logging
import random
from typing import Optional

import mysql.connector

from src.llm import extract_keywords, explain_match

logger = logging.getLogger(__name__)

# Full-text search fetches a larger pool, then we sample from top N for variety.
POOL_MULTIPLIER = 10
TOP_POOL_SIZE = 20


def keyword_search(
    conn: mysql.connector.MySQLConnection,
    keywords: list[str],
    limit: int = 10
) -> list[dict]:
    if not keywords:
        return []

    search_term = " ".join(keywords)
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT id, quote, author, category,
                       MATCH(quote, category) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
                FROM quotes
                WHERE MATCH(quote, category) AGAINST (%s IN NATURAL LANGUAGE MODE)
                ORDER BY score DESC
                LIMIT %s
            """, (search_term, search_term, limit * POOL_MULTIPLIER))
            pool = cursor.fetchall()

        if len(pool) > limit:
            top_pool = pool[:TOP_POOL_SIZE]
            results = random.sample(top_pool, min(limit, len(top_pool)))
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
        else:
            results = pool
    except mysql.connector.Error:
        results = like_search(conn, keywords, limit)

    return results


def like_search(
    conn: mysql.connector.MySQLConnection,
    keywords: list[str],
    limit: int = 10,
) -> list[dict]:
    """Simple LIKE fallback when full-text search is unavailable."""
    if not keywords:
        return []
    conditions = " OR ".join(["quote LIKE %s" for _ in keywords])
    params = [f"%{kw}%" for kw in keywords] + [limit]
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute(
            f"SELECT id, quote, author, category FROM quotes WHERE {conditions} LIMIT %s",
            params,
        )
        return cursor.fetchall()


def search_quotes(
    conn: mysql.connector.MySQLConnection,
    user_query: str,
    use_explanations: bool = False,
    limit: int = 5
) -> list[dict]:
    """
    Main search entrypoint. Uses LLM for keyword extraction, MySQL for retrieval.
    """
    query = user_query.strip() if user_query else ""
    if not query:
        logger.debug("Empty query provided")
        return []

    user_query = query[:500]
    keywords = extract_keywords(user_query)

    if not keywords:
        logger.debug("Could not extract keywords from: %r", user_query[:80])
        return []

    print(f"   Keywords: {keywords}")
    results = keyword_search(conn, keywords, limit=limit)

    if use_explanations and results:
        print("   Generating explanations (this may take a moment)...")
        for r in results[:3]:  # Only explain top 3 to keep it fast
            explanation = explain_match(r["quote"], user_query)
            r["explanation"] = explanation or "Matched your search keywords."
            explanation = explain_match(r["quote"], user_query)
            r["explanation"] = explanation or "Matched your search keywords."

    return results