import sys
import logging

# Enable readline-style editing and history (arrow keys, Ctrl+R, etc.)
try:
    import readline  # Unix / macOS — built-in
    readline.set_history_length(100)
except ImportError:
    try:
        import pyreadline3 as readline  # Windows
        readline.set_history_length(100)
    except ImportError:
        pass  # No readline available — input still works, just without history

from src.db import get_connection, ensure_schema
from src.importer import import_csv
from src.search import search_quotes

logger = logging.getLogger(__name__)


def truncate_quote(text: str, soft_limit: int = 200, buffer: int = 100) -> str:
    """
    Truncate at the nearest sentence boundary after soft_limit.
    Falls back to the nearest space, then hard-cuts as a last resort.
    """
    if len(text) <= soft_limit:
        return text

    search_area = text[soft_limit: soft_limit + buffer]
    for i, char in enumerate(search_area):
        if char in ".!?":
            return text[: soft_limit + i + 1]

    space_index = text.rfind(" ", 0, soft_limit)
    if space_index != -1:
        return text[:space_index] + "..."

    return text[:soft_limit] + "..."


def display_results(results: list[dict]) -> None:
    if not results:
        print("\n📭 No quotes found. Try a different search.\n")
        return

    print(f"\n✨ Found {len(results)} quote(s):\n")

    for i, r in enumerate(results, 1):
        quote = truncate_quote(r["quote"])

        category = r.get("category", "")
        if category:
            tags = [t.strip() for t in category.split(",")][:3]
            category_str = f"  [{', '.join(tags)}]"
        else:
            category_str = ""

        print(f"[{i}] \"{quote}\"")
        print(f"     — {r.get('author', 'Unknown')}{category_str}")
        if r.get("explanation"):
            print(f"     💡 {r['explanation']}")
        print()


def run_cli(
    db_host: str,
    db_user: str,
    db_password: str,
    db_name: str,
) -> None:

    conn = get_connection(db_host, db_user, db_password, db_name)
    if not conn:
        print("❌ Database unreachable. Check MySQL is running and your .env credentials.")
        sys.exit(1)

    ensure_schema(conn)

    print("📚 Book Quote Finder")
    print("Commands: 'import <path>', 'explain on/off', 'quit'")
    print("Tip: Use ↑ / ↓ arrow keys to navigate previous searches.\n")

    use_explanations = False

    while True:
        try:
            user_input = input("Search> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            logger.info("Session ended by user.")
            break

        if not user_input:
            continue

        elif user_input.lower() == "quit":
            print("Goodbye!")
            logger.info("Session ended by quit command.")
            break

        elif user_input.lower().startswith("import "):
            filepath = user_input[7:].strip()
            print(f"Importing {filepath}...")
            logger.info(f"Import requested: {filepath}")
            try:
                stats = import_csv(filepath, conn)
                print(
                    f"✅ Done: {stats['inserted']} inserted, "
                    f"{stats['skipped']} duplicates skipped, "
                    f"{stats['errors']} bad rows (see app.log for details)"
                )
            except FileNotFoundError as e:
                print(f"❌ {e}")
                logger.error(str(e))

        elif user_input.lower() == "explain on":
            use_explanations = True
            print("💡 Explanations enabled (slower — LLM generates a reason per quote)")

        elif user_input.lower() == "explain off":
            use_explanations = False
            print("💡 Explanations disabled")

        else:
            results = search_quotes(conn, user_input, use_explanations)
            display_results(results)

    conn.close()