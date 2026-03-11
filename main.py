import argparse
import logging

from src.cli import run_cli
from src.db import DEFAULT_DATABASE, DEFAULT_HOST, DEFAULT_PASSWORD, DEFAULT_USER

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Book Quote Finder")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    args = parser.parse_args()

    run_cli(args.host, args.user, args.password, args.database)