import pytest
from unittest.mock import MagicMock, patch
from src.search import keyword_search, like_search, search_quotes


def make_mock_conn(rows=None):
    """Helper to build a mock DB connection that returns given rows."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows or []
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


def test_keyword_search_returns_results():
    mock_conn = make_mock_conn([
        {"id": 1, "quote": "Keep going", "author": "Someone", "category": "motivation", "score": 1.5}
    ])
    results = keyword_search(mock_conn, ["motivation"], limit=5)
    assert len(results) == 1
    assert results[0]["author"] == "Someone"


def test_keyword_search_empty_keywords_returns_empty():
    mock_conn = make_mock_conn()
    results = keyword_search(mock_conn, [], limit=5)
    assert results == []


def test_like_search_returns_results():
    mock_conn = make_mock_conn([
        {"id": 2, "quote": "Failure is success", "author": "Author", "category": "wisdom"}
    ])
    results = like_search(mock_conn, ["failure"], limit=5)
    assert len(results) == 1
    assert "Failure" in results[0]["quote"]


def test_search_quotes_empty_query_returns_empty():
    mock_conn = make_mock_conn()
    results = search_quotes(mock_conn, "")
    assert results == []


def test_search_quotes_very_long_query_is_truncated():
    long_query = "a" * 1000
    mock_conn = make_mock_conn()
    with patch("src.search.extract_keywords", return_value=[]) as mock_extract:
        search_quotes(mock_conn, long_query)
        called_with = mock_extract.call_args[0][0]
        assert len(called_with) <= 500


def test_search_quotes_uses_llm_keywords():
    mock_conn = make_mock_conn([
        {"id": 3, "quote": "Lonely road", "author": "Poet", "category": "sad", "score": 2.0}
    ])
    with patch("src.search.extract_keywords", return_value=["lonely", "isolation"]):
        results = search_quotes(mock_conn, "something about loneliness")
        assert len(results) == 1


def test_search_quotes_no_keywords_returns_empty():
    mock_conn = make_mock_conn()
    with patch("src.search.extract_keywords", return_value=[]):
        results = search_quotes(mock_conn, "xyz")
        assert results == []