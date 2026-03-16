# Book Quote Finder

Book Quote Finder is a command‑line application for storing and searching book quotes in a MySQL database.

It combines:

- **MySQL full‑text search** for fast retrieval of relevant quotes.
- An **LLM (via Ollama + langchain‑ollama)** to extract keywords from natural‑language queries and optionally explain why a quote matches.
- A **pandas‑based CSV importer** that idempotently loads quotes into the database quickly.

---

## Features

- **Import quotes from CSV**
  - Expected columns: `quote`, `author`, `category`.
  - Uses pandas for fast chunked loading (batch size 2000).
  - Uses a SHA‑256 hash of the quote text to avoid duplicates on repeat imports.
  - Handles malformed rows gracefully and reports insert/skip/error counts.
  - Detailed per‑chunk progress is written to `app.log`.

- **Search quotes with natural language**
  - Send queries like "quotes about resilience after failure".
  - An LLM extracts 3–5 keywords, which drive MySQL full‑text search.
  - Notifies the user with `⚠️` when falling back from LLM to keyword search.
  - Falls back to a `LIKE` search if full‑text search is unavailable.

- **Robust LLM integration**
  - Uses `langchain‑ollama` instead of raw HTTP requests.
  - Automatic retry on network errors via `tenacity` (configurable attempts and backoff).
  - Two progressively simpler prompts are tried before giving up on JSON parsing.
  - Qwen "thinking mode" (`<think>...</think>` blocks) is disabled at the model level and stripped from responses as a safety net.
  - Short words (e.g. "USA", "war") are preserved in fallback keyword extraction.

- **Optional LLM explanations**
  - Toggle explanations on and off at the CLI (`explain on` / `explain off`).
  - When enabled, the LLM explains in one sentence why each top match is relevant.

- **Readable CLI output**
  - Readline‑style interface: use ↑ / ↓ arrow keys to navigate previous searches.
  - Smart sentence‑aware quote truncation (soft limit 200 characters, 100‑character buffer).
  - Author and up to 3 category tags per result.

- **Structured logging**
  - All internal events (DB connections, import progress, LLM calls, fallbacks) are written to `app.log` at DEBUG level.
  - Only `WARNING` and above appear on the console, keeping CLI output clean.

- **Environment‑based configuration**
  - All connection parameters and tuning values are loaded from a `.env` file via `config.py`.
  - No credentials are hardcoded in source files.

---

## Architecture Overview

```
book-quote-finder/
├── config.py           # Loads all settings from .env
├── main.py             # Entry point: initialises logging, parses args, calls run_cli
├── schema.sql          # Reference SQL for manual schema setup
├── requirements.txt
├── .env                # Your local credentials (not committed)
├── .env.example        # Template for .env
├── app.log             # Written at runtime (not committed)
└── src/
    ├── logger.py       # Centralised logging configuration
    ├── db.py           # get_connection, ensure_schema
    ├── importer.py     # Pandas-based CSV importer
    ├── llm.py          # langchain-ollama integration with retry logic
    ├── search.py       # Full-text and LIKE search orchestration
    └── cli.py          # User interaction loop and display
```

### Module responsibilities

- **`config.py`** — reads `DB_*`, `OLLAMA_*`, and `LOG_*` values from `.env` using `python‑dotenv`. Imported by all modules that need configuration.

- **`main.py`** — calls `setup_logging` before anything else, then parses optional CLI overrides and starts `run_cli`.

- **`src/logger.py`** — configures the root logger once: a file handler at `DEBUG` level (full detail) and a console handler at `WARNING` level (quiet by default).

- **`src/db.py`** — `get_connection` uses defaults from `config.py`; `ensure_schema` creates the `quotes` table and its indexes if they do not exist.

- **`src/importer.py`** — reads the CSV in chunks via `pandas.read_csv` (chunk size 2000, bad lines skipped, all columns as `str`). Normalises column names to lowercase. Logs per‑chunk progress to `app.log`.

- **`src/llm.py`** — builds a single `OllamaLLM` client with `think=False`. `_invoke` is wrapped with `tenacity` for automatic retries. `extract_keywords` tries two prompts, strips `<think>` blocks, parses JSON, and falls back to stopword removal, returning `(keywords, used_llm)`. `explain_match` generates a one‑sentence explanation.

- **`src/search.py`** — `keyword_search` fetches up to `limit × 10` candidates, samples from the top 20, and re‑sorts by score. Falls back to `like_search` on MySQL errors. `search_quotes` prints `⚠️` when the LLM was not used.

- **`src/cli.py`** — loads `readline` (or `pyreadline3` on Windows) for query history. Handles `import`, `explain on/off`, `quit`, and search queries. `truncate_quote` finds the nearest sentence boundary after 200 characters, then the nearest space, then hard‑cuts.

---

## Schema Design and Indexing

Single table `quotes` in the `book_quotes` database:

- **`id INT AUTO_INCREMENT PRIMARY KEY`** — surrogate key for stable row identity.
- **`quote TEXT NOT NULL`** — full quote text; no artificial length cap because quotes vary widely in length.
- **`author VARCHAR(255)`** — optional; 255 characters is sufficient for typical author names and keeps the index small.
- **`category VARCHAR(255)`** — optional comma‑separated tags or a single category.
- **`quote_hash CHAR(64) UNIQUE NOT NULL`** — SHA‑256 of the stripped `quote` text. The `UNIQUE` constraint combined with `INSERT IGNORE` makes imports idempotent: running the importer twice on the same file produces no duplicates.
- **`created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`** — records when the row was first inserted.

Indexes beyond the primary key:

- **`INDEX idx_author (author)`** — speeds up any future author‑based filtering without scanning the full table.
- **`FULLTEXT INDEX idx_quote_fulltext (quote, category)`** — powers `MATCH(...) AGAINST (...)` search. Preferable to `LIKE '%...%'` because it uses relevance scoring and scales to large datasets (the Kaggle dataset has ~500 000 rows).

---

## Prerequisites

- **Python 3.11** (or a compatible 3.x version).
- **MySQL 8.0** (or compatible):
  - A running MySQL server.
  - A database named `book_quotes` (or the name you set in `.env`).
  - A user with `CREATE`, `INSERT`, `SELECT` privileges on that database.
- **Ollama** (optional but recommended):
  - Running locally at `http://localhost:11434`.
  - Model `qwen2.5:0.5b` pulled (`ollama pull qwen2.5:0.5b`).
  - This ~0.5 B parameter model runs on CPU on a typical laptop and stays well under 2 GB RAM.

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
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Create your `.env` file**

   ```bash
   # Windows
   copy .env.example .env

   # macOS / Linux
   cp .env.example .env
   ```

   Open `.env` and fill in your values:

   ```env
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=yourpassword
   DB_NAME=book_quotes

   OLLAMA_MODEL=qwen2.5:0.5b
   OLLAMA_BASE_URL=http://localhost:11434
   LLM_TIMEOUT=15
   LLM_MAX_RETRIES=3

   LOG_LEVEL=INFO
   LOG_FILE=app.log
   ```

   > Do **not** wrap values in quotes. `DB_PASSWORD=secret` is correct; `DB_PASSWORD="secret"` is not.

5. **Create the MySQL database** (if it does not already exist)

   ```sql
   CREATE DATABASE book_quotes CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

   The table and indexes are created automatically on first run via `ensure_schema`.

---

## Configuration Reference

All settings are read from `.env` by `config.py`. You can also override the database settings at runtime with CLI flags (these take precedence over `.env`):

```bash
python main.py --host=localhost --user=book_user --password=secret --database=book_quotes
```

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | *(empty)* | MySQL password |
| `DB_NAME` | `book_quotes` | MySQL database name |
| `OLLAMA_MODEL` | `qwen2.5:0.5b` | Ollama model name (must match `ollama list`) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_TIMEOUT` | `15` | Seconds before an LLM request times out |
| `LLM_MAX_RETRIES` | `3` | Number of retry attempts on LLM failure |
| `LOG_LEVEL` | `INFO` | Minimum level written to `app.log` |
| `LOG_FILE` | `app.log` | Path to the log file |

---

## Running the Application

Start Ollama in a separate terminal (leave it running):

```bash
ollama serve
```

Then, from the project root:

```bash
python main.py
```

You will see:

```text
📚 Book Quote Finder
Commands: 'import <path>', 'explain on/off', 'quit'
Tip: Use ↑ / ↓ arrow keys to navigate previous searches.

Search>
```

---

## Importing Quotes from CSV

Use the `import` command from inside the CLI.

### CSV format

- **Required column:** `quote` — the text of the quote.
- **Optional columns:** `author`, `category` (comma‑separated tags).

Column names are normalised to lowercase automatically, so `Quote`, `QUOTE`, and `quote` are all accepted.

### Import command

```text
Search> import path/to/quotes.csv
Importing path/to/quotes.csv...
✅ Done: 499650 inserted, 38 duplicates skipped, 21 bad rows (see app.log for details)
```

- **Inserted** — new quotes saved to the database.
- **Skipped** — duplicates detected by `quote_hash` and ignored.
- **Bad rows** — rows with a missing or too‑short `quote` field; details are in `app.log`.

The importer works with the Kaggle ["Quotes‑500K"](https://www.kaggle.com/datasets/manann/quotes-500k) dataset. Running the import twice on the same file is safe — no rows are duplicated.

---

## Searching for Quotes

Type any natural‑language query at the `Search>` prompt:

```text
Search> quotes about resilience after failure
```

Example output:

```text
🔍 Searching for: 'quotes about resilience after failure'
   Keywords: ['resilience', 'failure', 'courage']

✨ Found 5 quote(s):

[1] "Success is not final, failure is not fatal: it is the courage to continue that counts."
     — Winston Churchill  [motivation, success]

[2] "Failure is simply the opportunity to begin again, this time more intelligently."
     — Henry Ford  [failure, resilience]
```

If the LLM is unavailable, you will see:

```text
   ⚠️  Using keyword fallback (LLM unavailable).
```

Search still works in this case — keyword quality may be slightly lower but results remain relevant.

### How search works

1. **Keyword extraction (`src/llm.py`)** — the query is sent to Ollama, which returns a JSON array of keywords. Two progressively simpler prompts are tried before falling back to stopword removal. Words of any length (including short ones like "USA") are preserved in the fallback.

2. **Full‑text search (`src/search.py`)** — uses `MATCH(...) AGAINST (... IN NATURAL LANGUAGE MODE)` on `quote` and `category`. Fetches up to 50 candidates, samples from the top 20 by relevance score for variety, then re‑sorts the sample by score before displaying.

3. **Result formatting (`src/cli.py`)** — quotes are truncated at the nearest sentence boundary after 200 characters. Up to 3 category tags are shown. If explanations are enabled, a one‑sentence LLM explanation is printed under each of the top 3 results.

---

## Explanations (LLM)

```text
Search> explain on
💡 Explanations enabled (slower — LLM generates a reason per quote)

Search> explain off
💡 Explanations disabled
```

When enabled, the LLM generates a one‑sentence explanation for the top 3 results. If Ollama is not running the search still completes — explanations are simply omitted.

---

## Logging

Logging is configured in `src/logger.py` and initialised in `main.py` before anything else runs.

- **`app.log`** — receives all events at `DEBUG` level and above. Check this file first when troubleshooting import errors, LLM failures, or unexpected search results.
- **Console** — only `WARNING` level and above is printed, keeping the CLI output clean.

To increase console verbosity, set `LOG_LEVEL=DEBUG` in your `.env`.

---

## Running Tests

```bash
pytest -v
```

The suite covers:

- Database helpers (`tests/test_db.py`)
- CSV importer (`tests/test_importer.py`)
- LLM integration and keyword extraction (`tests/test_llm.py`)
- Search orchestration and fallbacks (`tests/test_search.py`)

All tests use mocks and do not require a live MySQL connection or Ollama instance.

---

## Troubleshooting

**`❌ Database unreachable` at startup**
- Confirm MySQL is running.
- Verify your `.env` credentials. Run `python -c "import config; print(config.DB_PASSWORD)"` to confirm the value is being read correctly.
- Make sure the `.env` file is in the project root (same folder as `main.py`) and is not named `.env.txt`.

**`⚠️ Using keyword fallback` on every search**
- Ollama is not running. Start it with `ollama serve` in a separate terminal.
- Confirm the model name in `.env` matches exactly what `ollama list` shows (e.g. `qwen2.5:0.5b`).

**0 inserted, all skipped on import**
- This is correct behaviour on a repeat import — all rows already exist. Run `SELECT COUNT(*) FROM quotes;` in MySQL to confirm the data is present.

**No quotes found after import**
- Confirm the CSV has a non‑empty `quote` column header (any capitalisation is fine).
- Check `app.log` for per‑row error details from the import run.

**Encoding issues with CSV**
- The importer opens files as UTF‑8 with `errors="replace"`. Ensure your CSV is saved as UTF‑8.

---

## Edge Cases and Limitations

- **Malformed CSV rows** — rows with a missing or too‑short `quote` (under 5 characters) are counted as errors and skipped. Import continues. Details are logged to `app.log`.
- **LLM failures** — timeouts, connection errors, and unparseable JSON all fall back gracefully to stopword‑based keyword extraction. The user is notified with `⚠️`. Search still returns results.
- **LLM thinking mode** — `qwen2.5:0.5b` occasionally emits `<think>...</think>` blocks. These are disabled at the model level (`think=False`) and also stripped from responses before parsing.
- **Short keywords** — words like "USA", "war", or "joy" are preserved in fallback extraction (minimum length is 2 characters, not 4).
- **Empty or long queries** — empty queries are rejected immediately with a message. Queries over 500 characters are truncated before being sent to the LLM or database.
- **Non‑English queries** — passed through the same pipeline without special handling. The app will not crash, but relevance is tuned for English and may degrade for other languages.
- **Database unreachable** — `get_connection` returns `None`; the CLI prints a clear error and exits cleanly with a non‑zero status.
- **Relevance variety** — full‑text search can surface the same high‑scoring rows repeatedly for common words. The pool‑and‑sample strategy (top 20, sample 5) mitigates this but does not eliminate it entirely. A vector‑embedding approach would be a more complete solution.

---

## Reflections

**Hardest part** — making the LLM integration reliable enough to be useful. A small model like `qwen2.5:0.5b` running on CPU is fast and lightweight, but its output is inconsistent: it frequently returned malformed JSON, emitted thinking blocks, or produced the same keywords regardless of the query. Designing the fallback chain (two prompt attempts → stopword extraction) and stripping thinking blocks required more iteration than the happy path did.

**What I would improve with more time** — replace keyword‑based search with semantic vector embeddings (e.g. `sentence‑transformers`). This would enable genuine meaning‑based retrieval: "loneliness" would surface quotes about isolation and solitude even if those exact words never appear. I would also add a proper CLI progress bar for large CSV imports and explore `pgvector` or a dedicated vector store for the embedding index.

**What I learned** — graceful degradation is a design decision, not an afterthought. Every external dependency (LLM, database, CSV) needed a defined failure mode before writing the happy path. Building that structure early made the rest of the code simpler and more honest about what it actually guarantees.
