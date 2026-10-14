"""Envio dos dados ao Supabase pela API PostgREST, em lotes com nova tentativa."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

from ..config import load_environment
from .fields import NULLABLE_TIMESTAMP_FIELDS, PRICE_ALERT_FIELD, PRODUCT_DATA_FIELDS
from .stock_events import make_event_records

CHUNK_SIZE = 200
FETCH_PAGE_SIZE = 1000
SNAPSHOT_TABLES = {
    "categories": ("wedrop_categories", "category_url"),
    "products": ("wedrop_products", "product_id"),
    "stock_events": ("wedrop_stock_events", "event_id"),
}
MAX_ATTEMPTS = 6
REQUEST_TIMEOUT_SECONDS = 60
TRANSIENT_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})
REQUIRED_TABLES = {
    "wedrop_categories": "category_url",
    "wedrop_products": "product_id",
    "wedrop_stock_events": "event_id",
}

_logger = logging.getLogger("wedrop.scraper")


def _column_value(product: dict[str, Any], field: str) -> Any:
    """Valor da coluna; data vazia vai como NULL, porque o Supabase não aceita texto vazio em timestamptz."""
    value = product.get(field, "")
    if field in NULLABLE_TIMESTAMP_FIELDS and not value:
        return None
    return value


def is_configured() -> bool:
    """True quando as credenciais do Supabase estão disponíveis (ambiente ou .env)."""
    load_environment()
    has_url = bool(os.environ.get("SUPABASE_URL", "").strip())
    has_key = bool(
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.environ.get("SUPABASE_KEY", "").strip()
    )
    return has_url and has_key


class SupabaseRepository:
    """Grava categorias, produtos e movimentações com upsert (repetir não duplica)."""

    def __init__(self, url: str, api_key: str, timeout: int = 30):
        self.base_url = f"{url.rstrip('/')}/rest/v1"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "apikey": api_key,
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            }
        )

    @classmethod
    def from_environment(cls) -> SupabaseRepository:
        load_environment()
        url = os.environ.get("SUPABASE_URL", "").strip()
        api_key = (
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
            or os.environ.get("SUPABASE_KEY", "").strip()
        )
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", url),
                ("SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_KEY", api_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Supabase não configurado. Defina SUPABASE_URL e "
                "SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_KEY) no ambiente antes "
                "de iniciar a coleta."
            )
        return cls(url, api_key)

    def validate(self) -> None:
        """Falha antes da coleta se alguma tabela ou coluna necessária não existir."""
        for table, key in REQUIRED_TABLES.items():
            response = self.session.get(
                f"{self.base_url}/{table}",
                params={"select": key, "limit": "0"},
                timeout=self.timeout,
            )
            if not response.ok:
                raise RuntimeError(
                    f"Supabase indisponível para a tabela {table} "
                    f"(HTTP {response.status_code}): {response.text[:500]}. "
                    "Confirme SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY e execute "
                    "supabase_schema.sql no SQL Editor do projeto."
                )
        response = self.session.get(
            f"{self.base_url}/wedrop_products",
            params={"select": PRICE_ALERT_FIELD, "limit": "0"},
            timeout=self.timeout,
        )
        if not response.ok:
            raise RuntimeError(
                f"A coluna {PRICE_ALERT_FIELD} não existe em wedrop_products "
                f"(HTTP {response.status_code}). Execute no SQL Editor do Supabase o "
                "comando 'alter table' do arquivo supabase_schema.sql antes de coletar."
            )

    def save_category(self, category: dict[str, Any], mapped_products: int, captured_at: str) -> None:
        self._upsert(
            "wedrop_categories",
            [
                {
                    "category_url": category["url"],
                    "name": category["name"],
                    "expected_products": category.get("count"),
                    "mapped_products": mapped_products,
                    "updated_at": captured_at,
                }
            ],
            "category_url",
        )

    def save_products(self, products: list[dict[str, Any]], captured_at: str) -> None:
        product_rows = [
            {field: _column_value(product, field) for field in PRODUCT_DATA_FIELDS} | {"updated_at": captured_at}
            for product in products
        ]
        events_by_id = {
            event["event_id"]: event
            for product in products
            for event in make_event_records(product, captured_at)
        }
        self._upsert("wedrop_products", product_rows, "product_id")
        self._upsert("wedrop_stock_events", list(events_by_id.values()), "event_id")

    def fetch_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        """Lê categorias, produtos e movimentações inteiras (para o painel)."""
        return {
            name: self._fetch_table(table, key)
            for name, (table, key) in SNAPSHOT_TABLES.items()
        }

    def _fetch_table(self, table: str, order_key: str) -> list[dict[str, Any]]:
        """Lê a tabela em páginas: o PostgREST devolve um número limitado de linhas por chamada."""
        rows: list[dict[str, Any]] = []
        while True:
            response = self.session.get(
                f"{self.base_url}/{table}",
                params={"select": "*", "order": f"{order_key}.asc", "limit": FETCH_PAGE_SIZE, "offset": len(rows)},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            if not response.ok:
                raise RuntimeError(
                    f"Supabase não respondeu a leitura de {table} (HTTP {response.status_code}): "
                    f"{response.text[:300]}"
                )
            page = response.json()
            if not page:
                return rows
            rows.extend(page)

    def close(self) -> None:
        self.session.close()

    def _upsert(self, table: str, rows: list[dict[str, Any]], conflict: str) -> None:
        for start in range(0, len(rows), CHUNK_SIZE):
            self._post_chunk(table, rows[start : start + CHUNK_SIZE], conflict)

    def _post_chunk(self, table: str, chunk: list[dict[str, Any]], conflict: str) -> None:
        failure = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.session.post(
                    f"{self.base_url}/{table}",
                    params={"on_conflict": conflict},
                    json=chunk,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            except requests.exceptions.RequestException as exc:
                failure = f"falha de conexão: {exc}"
            else:
                if response.ok:
                    return
                if response.status_code not in TRANSIENT_STATUS_CODES:
                    raise RuntimeError(
                        f"Supabase rejeitou gravação em {table} "
                        f"(HTTP {response.status_code}): {response.text[:500]}"
                    )
                failure = f"HTTP {response.status_code}: {response.text[:500]}"

            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Supabase continuou indisponível para gravação em {table} "
                    f"após {MAX_ATTEMPTS} tentativas ({failure})."
                )
            _logger.warning(
                "Falha temporária ao gravar em %s no Supabase (tentativa %s/%s): %s",
                table,
                attempt,
                MAX_ATTEMPTS,
                failure,
            )
            time.sleep(3 ** (attempt - 1))
