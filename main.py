import argparse
import config
from src.logger import setup_logging
from src.cli import run_cli

if __name__ == "__main__":
    setup_logging(config.LOG_FILE, config.LOG_LEVEL)

    parser = argparse.ArgumentParser(description="Book Quote Finder")
    parser.add_argument("--host",     default=config.DB_HOST)
    parser.add_argument("--user",     default=config.DB_USER)
    parser.add_argument("--password", default=config.DB_PASSWORD)
    parser.add_argument("--database", default=config.DB_NAME)
    args = parser.parse_args()

    run_cli(args.host, args.user, args.password, args.database)