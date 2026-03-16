import logging
import random
import mysql.connector
from src.llm import extract_keywords, explain_match

logger = logging.getLogger(__name__)


def keyword_search(
    conn: mysql.connector.MySQLConnection,
    keywords: list[str],
    limit: int = 5,
) -> list[dict]:
    """Full-text search. Fetches a larger pool and samples for variety."""
    if not keywords:
        return []

    search_term = " ".join(keywords)
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, quote, author, category,
                   MATCH(quote, category) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
            FROM quotes
            WHERE MATCH(quote, category) AGAINST (%s IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT %s
            """,
            (search_term, search_term, limit * 10),
        )
        pool = cursor.fetchall()
        logger.debug(f"FULLTEXT search for {keywords!r} returned {len(pool)} candidates.")
    except mysql.connector.Error as e:
        logger.warning(f"FULLTEXT search failed, falling back to LIKE: {e}")
        pool = like_search(conn, keywords, limit)
    finally:
        cursor.close()

    if len(pool) > limit:
        top = pool[:20]  # sample only from top 20 by relevance
        results = random.sample(top, min(limit, len(top)))
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
    else:
        results = pool

    return results


def like_search(
    conn: mysql.connector.MySQLConnection,
    keywords: list[str],
    limit: int = 5,
) -> list[dict]:
    """Simple LIKE fallback search when FULLTEXT is unavailable."""
    if not keywords:
        return []
    cursor = conn.cursor(dictionary=True)
    conditions = " OR ".join(["quote LIKE %s"] * len(keywords))
    params = [f"%{kw}%" for kw in keywords] + [limit]
    cursor.execute(
        f"SELECT id, quote, author, category FROM quotes WHERE {conditions} LIMIT %s",
        params,
    )
    results = cursor.fetchall()
    cursor.close()
    logger.debug(f"LIKE search for {keywords!r} returned {len(results)} results.")
    return results


def search_quotes(
    conn: mysql.connector.MySQLConnection,
    user_query: str,
    use_explanations: bool = False,
    limit: int = 5,
) -> list[dict]:
    """
    Main search entrypoint.
    Uses LLM for keyword extraction with fallback to stopword removal.
    """
    if not user_query or not user_query.strip():
        print("[SEARCH] Query was empty — please type something to search.")
        return []

    user_query = user_query.strip()[:500]
    print(f"\n🔍 Searching for: '{user_query}'")

    keywords, used_llm = extract_keywords(user_query)

    if not used_llm:
        print("   ⚠️  Using keyword fallback (LLM unavailable).")

    if not keywords:
        print("[SEARCH] Could not extract any keywords from your query.")
        logger.warning(f"No keywords extracted from query: {user_query!r}")
        return []

    print(f"   Keywords: {keywords}")
    results = keyword_search(conn, keywords, limit=limit)

    if use_explanations and results:
        print("   Generating explanations...")
        for r in results[:3]:
            explanation = explain_match(r["quote"], user_query)
            r["explanation"] = explanation or "Matched your search keywords."

    logger.info(f"Search '{user_query}' → {len(results)} results (LLM used: {used_llm})")
    return results