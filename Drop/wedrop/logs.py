"""Log de progresso: grava no arquivo e mostra no console."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import LOG_FILE

PROGRESS_LOGGER = logging.getLogger("wedrop.scraper")
_FORMAT = "%(asctime)s %(levelname)s %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_progress_logging() -> None:
    """Configura os handlers uma única vez, mesmo que seja chamado várias vezes."""
    if PROGRESS_LOGGER.handlers:
        return
    PROGRESS_LOGGER.setLevel(logging.INFO)
    PROGRESS_LOGGER.propagate = False

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    # Terminais do Windows em cp1252 não exibem todos os símbolos; não deve derrubar o log.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    console_handler = logging.StreamHandler(sys.stdout)
    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
        PROGRESS_LOGGER.addHandler(handler)


def log_progress(message: str) -> None:
    PROGRESS_LOGGER.info(message)
