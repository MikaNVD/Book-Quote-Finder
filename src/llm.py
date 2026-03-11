import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:0.5b"


def ask_llm(prompt: str, timeout: int = 15) -> Optional[str]:
    """
    Send a prompt to local Ollama. Returns response text or None on failure.
    """
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 200}
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except requests.exceptions.Timeout:
        logger.warning("LLM request timed out — falling back to keyword search.")
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Ollama not running — falling back to keyword search.")
        return None
    except Exception as e:
        logger.exception("Unexpected LLM error: %s", e)
        return None


def extract_keywords(user_query: str) -> list[str]:
    """
    Use LLM to extract meaningful search keywords from a natural language query.
    Falls back to simple word splitting if LLM fails.
    """
    if not user_query or len(user_query.strip()) < 2:
        return []

    prompt = f"""Extract 3-5 single keywords for searching book quotes based on this query.
Return ONLY a JSON array of lowercase strings. No explanation.
Query: "{user_query}"
Example output: ["hope", "failure", "resilience"]
Output:"""

    result = ask_llm(prompt)

    if result:
        try:
            # Strip any markdown fences if model adds them
            clean = result.replace("```json", "").replace("```", "").strip()
            keywords = json.loads(clean)
            if isinstance(keywords, list):
                return [str(k).lower().strip() for k in keywords if k][:5]
        except (json.JSONDecodeError, ValueError):
            pass  # Fall through to fallback

    # Fallback: naive keyword extraction (remove stopwords)
    stopwords = {
        "a", "about", "and", "any", "best", "concerning", "find", "for",
        "get", "give", "good", "great", "in", "interesting", "like",
        "looking", "me", "need", "nice", "or", "please", "quote", "quotes",
        "regarding", "related", "search", "show", "some", "something",
        "the", "theme", "topic", "want", "with",
    }
    words = user_query.lower().split()
    return [w for w in words if w not in stopwords and len(w) > 3][:5]


def explain_match(quote: str, user_query: str) -> Optional[str]:
    """Ask LLM why a quote matches the user's query."""
    prompt = f"""In one sentence, explain why this quote matches the search "{user_query}":
Quote: "{quote[:200]}"
Answer:"""
    return ask_llm(prompt, timeout=10)