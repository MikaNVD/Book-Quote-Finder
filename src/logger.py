import logging
import sys


def setup_logging(log_file: str, log_level: str) -> None:
    """
    Configure the root logger once at app startup.
    - File handler: captures DEBUG and above (full detail for troubleshooting)
    - Console handler: WARNING and above only (keeps CLI output clean)
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if called more than once
    if root_logger.handlers:
        return

    file_fmt = logging.Formatter(
        "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_fmt = logging.Formatter("%(levelname)s: %(message)s")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_fmt)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)