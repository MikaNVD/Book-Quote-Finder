import pytest
from unittest.mock import MagicMock, patch
from src.importer import hash_quote, import_csv


def test_hash_quote_consistent():
    assert hash_quote("Hello world") == hash_quote("Hello world")

def test_hash_quote_different_inputs():
    assert hash_quote("Hello") != hash_quote("World")

def test_hash_quote_strips_whitespace():
    assert hash_quote("  hello  ") == hash_quote("hello")

def test_import_csv_missing_file():
    mock_conn = MagicMock()
    with pytest.raises(FileNotFoundError):
        import_csv("/nonexistent/path.csv", mock_conn)

def test_import_csv_skips_empty_quotes(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text('quote,author,category\n,Unknown,\nHello world,Author,cat\n')
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1
    mock_conn.cursor.return_value = mock_cursor
    stats = import_csv(str(csv_file), mock_conn)
    assert stats["errors"] == 1