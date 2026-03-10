from unittest.mock import patch, MagicMock
from src.llm import extract_keywords, ask_llm
import requests


def test_extract_keywords_fallback_on_llm_failure():
    with patch("src.llm.ask_llm", return_value=None):
        result = extract_keywords("quotes about loneliness")
        assert "loneliness" in result

def test_extract_keywords_empty_query():
    assert extract_keywords("") == []

def test_ask_llm_timeout_returns_none():
    with patch("requests.post", side_effect=requests.exceptions.Timeout):
        result = ask_llm("test prompt")
        assert result is None

def test_extract_keywords_parses_llm_json():
    with patch("src.llm.ask_llm", return_value='["hope", "failure"]'):
        result = extract_keywords("hopeful quotes about failure")
        assert "hope" in result
        assert "failure" in result

def test_extract_keywords_handles_garbage_llm_response():
    with patch("src.llm.ask_llm", return_value="not valid json at all!!!"):
        result = extract_keywords("motivational quotes")
        assert isinstance(result, list)