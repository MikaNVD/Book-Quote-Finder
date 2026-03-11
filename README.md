# Book Quote Finder

Book Quote Finder is a small command‑line application for storing and searching book quotes in a MySQL database.

It combines:

- **MySQL full‑text search** for fast retrieval of relevant quotes.
- An **LLM (via Ollama)** to extract keywords from natural‑language queries and optionally explain why a quote matches.
- A simple **CSV importer** that idempotently loads quotes into the database.

---

## Features

- **Import quotes from CSV**
  - Expected columns: `quote`, `author`, `category`.
  - Uses a SHA‑256 hash of the quote text to avoid duplicates.
  - Handles malformed rows gracefully and reports insert/skip/error counts.

- **Search quotes with natural language**
  - Send queries like “quotes about resilience after failure”.
  - An LLM extracts 3–5 keywords, which are used with MySQL full‑text search.
  - Falls back to a `LIKE` search if full‑text search is unavailable.

- **Optional LLM explanations**
  - Toggle explanations on and off at the CLI (`explain on` / `explain off`).
  - When enabled, the LLM explains (in one sentence) why each top match is relevant.

- **Readable CLI output**
  - Pretty, truncated quotes (with sentence‑aware truncation).
  - Author and up to 3 category tags per result.
  - Clear feedback during imports and searches.

- **Safe, test‑covered implementation**
  - Cursor usage via context managers.
  - Structured logging for internals; friendly `print` messages for users.
  - A test suite (`pytest`) covering DB helpers, importer, LLM integration, and search logic.

---

## Architecture Overview

High‑level structure:

- `main.py`  
  CLI entry point. Configures logging, parses arguments, calls `run_cli`.

- `src/cli.py`  
  User interaction loop:
  - Connects to MySQL and ensures the schema is present.
  - Handles commands: `import <path>`, `explain on`, `explain off`, `quit`, or a search query.
  - Displays search results in a human‑friendly way.

- `src/db.py`  
  Database utilities:
  - `get_connection(...)` – opens a MySQL connection.
  - `ensure_schema(conn)` – creates the `quotes` table with indexes if needed.
  - Defines `DEFAULT_HOST`, `DEFAULT_USER`, `DEFAULT_PASSWORD`, `DEFAULT_DATABASE`.

- `src/importer.py`  
  CSV import:
  - `hash_quote(text)` – SHA‑256 hash for deduplication.
  - `import_csv(filepath, conn, batch_size=500)` – imports quotes in batches using `INSERT IGNORE`.

- `src/llm.py`  
  LLM integration via Ollama:
  - `ask_llm(prompt, timeout)` – low‑level API call.
  - `extract_keywords(user_query)` – robust keyword extraction with fallback.
  - `explain_match(quote, user_query)` – short explanation of why a quote matches.

- `src/search.py`  
  Search orchestration:
  - `keyword_search(conn, keywords, limit)` – MySQL full‑text search with controlled randomness.
  - `like_search(conn, keywords, limit)` – simple `LIKE` search fallback.
  - `search_quotes(conn, user_query, use_explanations, limit)` – main search entrypoint.

Tests are under `tests/` and validate each of these components.

---

## Prerequisites

- **Python**: 3.11 (or a compatible 3.x version).
- **MySQL / MariaDB**:
  - A running MySQL server.
  - A database (schema) created for this app, default: `book_quotes`.
  - A user with permissions to create tables and insert/select rows in that database.
- **Ollama** (optional but recommended):
  - Running locally at `http://localhost:11434`.
  - Model `qwen2.5:0.5b` available (or adjust the model in `src/llm.py`).

---

## Installation

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd book-quote-finder
   ```

2. **Create and activate a virtual environment (recommended)**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   # source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure MySQL**

   - Create a database (if not already created):

     ```sql
     CREATE DATABASE book_quotes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     ```

   - Ensure a user exists with access to this database (defaults assume `root` with no password, which you should change in production).

---

## Configuration

Database defaults are defined in `src/db.py`:

```python
DEFAULT_HOST = "localhost"
DEFAULT_USER = "root"
DEFAULT_PASSWORD = ""
DEFAULT_DATABASE = "book_quotes"
```

These are used both by:

- `get_connection()` in `src/db.py`
- CLI arguments in `main.py` (as default values)

You can override them at runtime via CLI flags:

- `--host`
- `--user`
- `--password`
- `--database`

Example:

```bash
python main.py --host=localhost --user=book_user --password=secret --database=book_quotes
```

If desired, you can also modify the constants in `src/db.py` to change the defaults globally.

---

## Running the Application

From the project root:

```bash
python main.py
```

By default, this connects to MySQL using the `DEFAULT_*` values in `src/db.py`.

If the database is reachable:

- The schema is created (if missing).
- You will see a banner and prompt:

```text
📚 Book Quote Finder
Commands: 'import <path>', 'explain on/off', 'quit'

Search>
```

---

## Importing Quotes from CSV

Use the `import` command from inside the CLI.

### CSV Format

- **Required column:**
  - `quote` – the text of the quote.
- **Optional columns:**
  - `author` – free‑text author name.
  - `category` – comma‑separated tags or a single category.

Example `quotes.csv`:

```csv
quote,author,category
"Success is not final, failure is not fatal: it is the courage to continue that counts.",Winston Churchill,motivation,success
"Not all those who wander are lost.",J.R.R. Tolkien,adventure
"To be, or not to be, that is the question.",William Shakespeare,classic,philosophy
```

> Note: Extra columns are ignored; rows without a valid `quote` are counted as errors and skipped.

### Import command

From the `Search>` prompt:

```text
Search> import path/to/quotes.csv
Importing path/to/quotes.csv...
✅ Done: 123 inserted, 5 skipped, 2 errors
```

- **Inserted** – number of new quotes actually saved.
- **Skipped** – duplicates ignored by the database (same `quote` text).
- **Errors** – malformed or invalid rows (e.g. missing or too‑short `quote`).

Internally, deduplication is done via:

- A SHA‑256 hash of the stripped `quote` string.
- A unique index on `quote_hash` in the `quotes` table.
- `INSERT IGNORE` semantics.

---

## Searching for Quotes

At the `Search>` prompt, type any natural‑language query:

```text
Search> quotes about resilience after failure
```

You will see something like:

```text
🔍 Searching for: 'quotes about resilience after failure'
✨ Found 3 quote(s):

[1] "Success is not final, failure is not fatal: it is the courage to continue that counts."
     — Winston Churchill  [motivation, success]

[2] "Failure is simply the opportunity to begin again, this time more intelligently."
     — Henry Ford  [failure, resilience]
```

### How search works

1. **Keyword extraction (`src/llm.py`)**
   - The query is sent to the LLM (Ollama) which returns a JSON array of keywords.
   - If the LLM fails, times out, or returns garbage:
     - A simple fallback removes stopwords and uses remaining words as keywords.

2. **Full‑text search (`src/search.py`)**
   - Uses `MATCH(...) AGAINST (... IN NATURAL LANGUAGE MODE)` on `quote` and `category`.
   - Fetches a larger pool of results, then samples and reorders them by score for some variety.
   - If full‑text search is not available, falls back to a `LIKE` search.

3. **Result formatting (`src/cli.py`)**
   - Quotes are truncated at sentence boundaries near 200 characters (configurable).
   - Up to 3 category tags are displayed.
   - If explanations are enabled, they are printed beneath each top result.

---

## Explanations (LLM)

You can turn match explanations on and off from the CLI.

- **Enable explanations:**

  ```text
  Search> explain on
  💡 Explanations enabled (slower)
  ```

- **Disable explanations:**

  ```text
  Search> explain off
  💡 Explanations disabled
  ```

When enabled, the app asks the LLM to explain, in one sentence, why a given quote matches your query. This is done for the top few results to keep performance reasonable.

> If Ollama is not running or times out, the search still works; you just won’t see explanations.

---

## Logging

- Logging is configured in `main.py` via:

  ```python
  logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
  ```

- Internal components (`db`, `llm`, `importer`, `search`) use the standard `logging` module.
- User‑facing messages (CLI prompts and results) continue to use `print` for clarity.

To increase verbosity for debugging, you can modify `level=` to `logging.INFO` or `logging.DEBUG`.

---

## Development

### Running tests

From the project root:

```bash
pytest -v
```

The suite covers:

- Database helpers (`src/db.py`).
- CSV importer (`src/importer.py`).
- LLM integration and keyword extraction (`src/llm.py`).
- Search orchestration and fallbacks (`src/search.py`).

All tests should pass before committing changes.

### Code style

The code follows standard Python best practices:

- Type hints on public functions.
- Context managers for DB cursors.
- No `print` statements in library code paths; use `logging` instead.
- Clear separation between:
  - CLI / presentation (`src/cli.py`)
  - Business logic (`src/search.py`, `src/importer.py`)
  - Infrastructure (`src/db.py`, `src/llm.py`)

---

## Troubleshooting

- **`❌ Database unreachable...` at startup**
  - Ensure MySQL is running.
  - Verify host/user/password/database.
  - Try overriding via CLI flags:
    ```bash
    python main.py --host=localhost --user=<user> --password=<pass> --database=book_quotes
    ```

- **No quotes found even after import**
  - Confirm that the CSV has a non‑empty `quote` column.
  - Check the DB directly:
    ```sql
    SELECT COUNT(*) FROM quotes;
    ```
  - Make sure you are connecting to the same database you imported into.

- **LLM explanations not showing**
  - Check that Ollama is running.
  - Confirm the endpoint and model in `src/llm.py`:
    - `OLLAMA_URL = "http://localhost:11434/api/generate"`
    - `MODEL = "qwen2.5:0.5b"`
  - If problems persist, try running with explanations off (`explain off`) to confirm core search still works.

- **Encoding issues with CSV**
  - Importer opens files as UTF‑8 with `errors="replace"`.
  - If you see strange characters, ensure your CSV is saved as UTF‑8.

---
