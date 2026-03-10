import pytest
from unittest.mock import MagicMock, patch, call
from src.db import get_connection, ensure_schema


def test_get_connection_returns_none_on_failure():
    with patch("src.db.mysql.connector.connect", side_effect=Exception("Connection refused")):
        result = get_connection(host="localhost", user="root", password="wrong", database="test")
        assert result is None


def test_get_connection_called_with_correct_params():
    mock_conn = MagicMock()
    with patch("src.db.mysql.connector.connect", return_value=mock_conn) as mock_connect:
        result = get_connection(host="localhost", user="root", password="pass", database="book_quotes")
        mock_connect.assert_called_once_with(
            host="localhost",
            user="root",
            password="pass",
            database="book_quotes",
            connection_timeout=5
        )
        assert result == mock_conn


def test_get_connection_returns_connection_on_success():
    mock_conn = MagicMock()
    with patch("src.db.mysql.connector.connect", return_value=mock_conn):
        result = get_connection()
        assert result is not None


def test_ensure_schema_executes_create_table():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    ensure_schema(mock_conn)

    mock_cursor.execute.assert_called_once()
    sql_called = mock_cursor.execute.call_args[0][0]
    assert "CREATE TABLE IF NOT EXISTS quotes" in sql_called


def test_ensure_schema_commits_and_closes():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    ensure_schema(mock_conn)

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()