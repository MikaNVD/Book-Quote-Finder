import argparse
from src.cli import run_cli

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Book Quote Finder")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", default="book_quotes")
    args = parser.parse_args()

    run_cli(args.host, args.user, args.password, args.database)