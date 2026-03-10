import mysql.connector
import random
from typing import Optional
from src.llm import extract_keywords, explain_match


def keyword_search(
    conn: mysql.connector.MySQLConnection,
    keywords: list[str],
    limit: int = 10
) -> list[dict]:
    if not keywords:
        return []

    search_term = " ".join(keywords)
    cursor = conn.cursor(dictionary=True)

    try:
        # Get a larger pool first, then randomly sample from it
        cursor.execute("""
            SELECT id, quote, author, category,
                   MATCH(quote, category) AGAINST (%s IN NATURAL LANGUAGE MODE) AS score
            FROM quotes
            WHERE MATCH(quote, category) AGAINST (%s IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT %s
        """, (search_term, search_term, limit * 10))  # fetch 50, not 5
        
        pool = cursor.fetchall()
        
        # Randomly sample from the pool so results vary each time
        if len(pool) > limit:
            # Take top 20 by score, then randomly sample from those only
            top_pool = pool[:20]
            results = random.sample(top_pool, min(limit, len(top_pool)))
            # Re-sort the sample by score descending
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
        else:
            results = pool
            
    except mysql.connector.Error:
        results = like_search(conn, keywords, limit)
    finally:
        cursor.close()

    return results


def like_search(
    conn: mysql.connector.MySQLConnection,
    keywords: list[str],
    limit: int = 10
) -> list[dict]:
    """Simple LIKE fallback search."""
    cursor = conn.cursor(dictionary=True)
    conditions = " OR ".join(["quote LIKE %s" for _ in keywords])
    params = [f"%{kw}%" for kw in keywords] + [limit]
    cursor.execute(f"SELECT id, quote, author, category FROM quotes WHERE {conditions} LIMIT %s", params)
    results = cursor.fetchall()
    cursor.close()
    return results


def search_quotes(
    conn: mysql.connector.MySQLConnection,
    user_query: str,
    use_explanations: bool = False,
    limit: int = 5
) -> list[dict]:
    """
    Main search entrypoint. Uses LLM for keyword extraction, MySQL for retrieval.
    """
    if not user_query or not user_query.strip():
        print("[SEARCH] Empty query provided.")
        return []

    # Truncate absurdly long queries
    user_query = user_query.strip()[:500]

    print(f"\n🔍 Searching for: '{user_query}'")
    keywords = extract_keywords(user_query)

    if not keywords:
        print("[SEARCH] Could not extract keywords.")
        return []

    print(f"   Keywords: {keywords}")
    results = keyword_search(conn, keywords, limit=limit)

    if use_explanations and results:
        print("   Generating explanations (this may take a moment)...")
        for r in results[:3]:  # Only explain top 3 to keep it fast
            explanation = explain_match(r["quote"], user_query)
            r["explanation"] = explanation or "Matched your search keywords."

    return results