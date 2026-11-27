
import logging
from pathlib import Path

from decisioniq.utils.config import (
    load_config,
    PROJECT_ROOT
)


def get_logger(name: str) -> logging.Logger:

    config = load_config()
    settings = config.get("logging", {})

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = settings.get("level", "INFO").upper()
    logger.setLevel(level)
    logger.propagate = False

    log_path = Path(
        settings.get("file", "logs/decisioniq.log")
    )

    if not log_path.is_absolute():
        log_path = PROJECT_ROOT / log_path

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | "
        "%(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        log_path,
        encoding="utf-8"
    )

    console_handler = logging.StreamHandler()

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
