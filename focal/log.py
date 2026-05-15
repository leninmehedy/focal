import logging
import sys
from datetime import date
from pathlib import Path

_logger: logging.Logger | None = None


def setup(log_dir: Path) -> logging.Logger:
    global _logger
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{date.today().isoformat()}.log"

    fmt = "[%(asctime)s] [%(levelname)-5s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    logger = logging.getLogger("focal")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    logger.addHandler(fh)

    if sys.stdout.isatty():
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(logging.Formatter(fmt, datefmt))
        logger.addHandler(ch)

    _logger = logger
    return logger


def get() -> logging.Logger:
    return _logger or logging.getLogger("focal")
