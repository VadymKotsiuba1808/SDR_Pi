import logging
import sys
from typing import Optional

import colorlog

COLOR_FORMAT = (
    "%(log_color)s%(asctime)s | %(name)s | %(levelname)s%(reset)s | %(message)s"
)

FILE_FORMAT = "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s"

LOG_TIME_FORMAT = "%d-%m %H:%M:%S"


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> None:
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_formatter = colorlog.ColoredFormatter(
        COLOR_FORMAT,
        datefmt=LOG_TIME_FORMAT,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
    stdout_handler.setFormatter(stdout_formatter)

    handlers: list[logging.Handler] = [stdout_handler]

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        handlers.append(file_handler)

    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
