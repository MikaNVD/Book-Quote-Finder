import json
import logging
import re
from typing import Optional

from langchain_ollama import OllamaLLM
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    RetryError,
)

import config

logger = logging.getLogger(__name__)

# Build LLM client once using config
_llm = OllamaLLM(
    model=config.OLLAMA_MODEL,
    base_url=config.OLLAMA_BASE_URL,
    temperature=0.3,
    num_predict=200,
    timeout=config.LLM_TIMEOUT,
)


@retry(
    stop=stop_after_attempt(config.LLM_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _invoke(prompt: str) -> str:
    """Raw LLM call with automatic retry on any exception."""
    return _llm.invoke(prompt)


def ask_llm(prompt: str) -> Optional[str]:
    try:
        result = _invoke(prompt)
        if not result:
            return None
        # Strip thinking blocks qwen models emit before the real response
        result = re.sub(r"<think>.*?</think>", "", result, flags=re.DOTALL).strip()
        logger.debug(f"LLM response received: {result[:80]!r}")
        return result if result else None
    except RetryError as e:
        logger.warning(f"LLM failed after {config.LLM_MAX_RETRIES} retries: {e}")
        return None
    except Exception as e:
        logger.warning(f"LLM unexpected error: {e}")
        return None
        

def _parse_keyword_json(raw: str) -> Optional[list[str]]:
    """Extract a JSON array of strings from raw LLM output."""
    clean = raw.replace("```json", "").replace("```", "").strip()
    start = clean.find("[")
    end = clean.rfind("]") + 1
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(clean[start:end])
        if isinstance(parsed, list):
            return [str(k).lower().strip() for k in parsed if str(k).strip()][:5]
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def extract_keywords(user_query: str) -> tuple[list[str], bool]:
    """
    Extract search keywords from a natural language query.

    Tries two progressively simpler prompts before falling back to
    naive stopword removal. Returns (keywords, used_llm).
    """
    if not user_query or len(user_query.strip()) < 2:
        return [], False

    # Two prompt attempts: detailed first, simpler second
    prompts = [
        (
            f'Extract 3-5 single search keywords from this query.\n'
            f'Return ONLY a JSON array of lowercase strings. No explanation, no markdown.\n'
            f'Query: "{user_query}"\n'
            f'Output:'
        ),
        (
            f'Keywords for "{user_query}". '
            f'JSON array only, e.g. ["word1","word2"]: '
        ),
    ]

    for attempt_num, prompt in enumerate(prompts, start=1):
        raw = ask_llm(prompt)
        if raw:
            keywords = _parse_keyword_json(raw)
            if keywords:
                logger.info(f"LLM keywords (attempt {attempt_num}): {keywords}")
                return keywords, True
            logger.warning(
                f"LLM attempt {attempt_num} returned unparseable JSON: {raw[:80]!r}"
            )

    # Fallback: naive stopword removal
    print("[SEARCH] LLM unavailable or returned invalid response — using keyword fallback.")
    logger.info("Falling back to stopword keyword extraction.")

    stopwords = {
        "find", "me", "about", "some", "a", "an", "the", "in", "for",
        "and", "or", "give", "show", "quotes", "something", "quote",
        "want", "need", "looking", "search", "get", "please", "like",
        "related", "topic", "regarding", "with", "any", "good", "great",
        "best", "nice", "interesting", "something", "i", "my", "want",
    }
    words = user_query.lower().split()
    fallback = [w.strip(".,!?") for w in words
                if w not in stopwords and len(w) > 1  # ← keeps anything 2+ characters
                ]
    return fallback, False


def explain_match(quote: str, user_query: str) -> Optional[str]:
    """Ask the LLM to explain in one sentence why a quote matches the query."""
    prompt = (
        f'In one sentence, explain why this quote matches the search "{user_query}":\n'
        f'Quote: "{quote[:200]}"\n'
        f'Answer:'
    )
    result = ask_llm(prompt)
    if result:
        logger.debug(f"Explanation generated for query '{user_query}'")
    return result