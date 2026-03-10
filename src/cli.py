import sys
from src.db import get_connection, ensure_schema
from src.importer import import_csv
from src.search import search_quotes


def truncate_quote(text: str, soft_limit: int = 200, buffer: int = 100) -> str:
    """
    Truncate at the end of a sentence near soft_limit.
    Falls back to nearest space, then hard cuts if nothing found.
    """
    if len(text) <= soft_limit:
        return text

    # Search for sentence-ending delimiter within the buffer range
    search_area = text[soft_limit: soft_limit + buffer]
    for i, char in enumerate(search_area):
        if char in ".!?":
            return text[:soft_limit + i + 1]

    # Fallback: find nearest space before soft_limit
    space_index = text.rfind(" ", 0, soft_limit)
    if space_index != -1:
        return text[:space_index] + "..."

    # Hard cut as last resort
    return text[:soft_limit] + "..."


def display_results(results: list[dict]) -> None:
    if not results:
        print("\n📭 No quotes found. Try a different search.\n")
        return

    print(f"\n✨ Found {len(results)} quote(s):\n")

    for i, r in enumerate(results, 1):
        quote = truncate_quote(r['quote'])

        # Show max 3 category tags
        category = r.get('category', '')
        if category:
            tags = [t.strip() for t in category.split(',')][:3]
            category_str = f"  [{', '.join(tags)}]"
        else:
            category_str = ""

        print(f"[{i}] \"{quote}\"")
        print(f"     — {r.get('author', 'Unknown')}{category_str}")
        if r.get("explanation"):
            print(f"     💡 {r['explanation']}")
        print()


def run_cli(db_host: str = "localhost", db_user: str = "root",
            db_password: str = "", db_name: str = "book_quotes") -> None:

    conn = get_connection(db_host, db_user, db_password, db_name)
    if not conn:
        print("❌ Database unreachable. Check MySQL is running and credentials are correct.")
        sys.exit(1)

    ensure_schema(conn)
    print("📚 Book Quote Finder")
    print("Commands: 'import <path>', 'explain on/off', 'quit'\n")

    use_explanations = False

    while True:
        try:
            user_input = input("Search> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        elif user_input.lower() == "quit":
            print("Goodbye!")
            break
        elif user_input.lower().startswith("import "):
            filepath = user_input[7:].strip()
            print(f"Importing {filepath}...")
            try:
                stats = import_csv(filepath, conn)
                print(f"✅ Done: {stats['inserted']} inserted, "
                      f"{stats['skipped']} skipped, {stats['errors']} errors")
            except FileNotFoundError as e:
                print(f"❌ {e}")
        elif user_input.lower() == "explain on":
            use_explanations = True
            print("💡 Explanations enabled (slower)")
        elif user_input.lower() == "explain off":
            use_explanations = False
            print("💡 Explanations disabled")
        else:
            results = search_quotes(conn, user_input, use_explanations)
            display_results(results)

    conn.close()