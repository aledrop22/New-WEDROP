"""Caminhos, endereços e limites do sistema, reunidos em um único lugar."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "dados"
BACKUP_DIR = DATA_DIR / "backups"
PRODUCTS_FILE = DATA_DIR / "data.json"
DATABASE_FILE = DATA_DIR / "wedrop_monitoramento.db"
RUN_STATE_FILE = DATA_DIR / "estado_coleta.json"
BROWSER_SESSION_FILE = DATA_DIR / "storage_state.json"
LOG_FILE = PROJECT_DIR / "logs" / "scraper_runs.log"
ENV_FILE = PROJECT_DIR / ".env"

BASE_URL = "https://dash.wedrop.com.br"
PRODUCTS_PER_PAGE = 100
PRODUCT_READ_ATTEMPTS = 3
DEFAULT_WORKERS = 3
BATCH_SIZE = 10
BACKUPS_TO_KEEP_UNCOMPRESSED = 3

# Recursos que não alteram o texto lido; bloquear acelera cada página.
BLOCKED_RESOURCE_TYPES = frozenset({"image", "media", "font"})


def load_environment() -> None:
    """Carrega o .env local sem sobrescrever variáveis já definidas no processo."""
    load_dotenv(ENV_FILE, override=False)
