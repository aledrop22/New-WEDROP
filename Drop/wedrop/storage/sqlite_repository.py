"""Histórico local em SQLite: categorias, produtos e movimentações de estoque."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .fields import PRODUCT_DATA_FIELDS, PRODUCT_FIELDS
from .product_status import effective_status
from .stock_events import make_event_records, parse_event_datetime

_SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    category_url TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    expected_products INTEGER,
    mapped_products INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    url TEXT NOT NULL,
    sku TEXT,
    ean TEXT,
    price TEXT,
    availability TEXT,
    stock TEXT,
    total_stock_count TEXT,
    real_balance TEXT,
    is_active TEXT,
    supplier TEXT,
    cnpj TEXT,
    origin_state TEXT,
    ncm TEXT,
    weight TEXT,
    height TEXT,
    width TEXT,
    length TEXT,
    description TEXT,
    number_sales TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS stock_events (
    event_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    movement_type TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    event_at TEXT,
    event_at_raw TEXT NOT NULL,
    nf_key TEXT,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
CREATE INDEX IF NOT EXISTS stock_events_kind_date_idx
    ON stock_events (event_kind, event_at);
CREATE INDEX IF NOT EXISTS stock_events_product_date_idx
    ON stock_events (product_id, event_at);
"""

# Situação do produto a partir do texto livre do campo is_active.
_ACTIVE_SQL = (
    "(LOWER(TRIM(wedrop_status(p.is_active, p.availability))) LIKE '%ativo%' "
    "OR LOWER(TRIM(wedrop_status(p.is_active, p.availability))) IN ('active', 'true', '1', 'sim'))"
)
_INACTIVE_SQL = (
    "(LOWER(TRIM(wedrop_status(p.is_active, p.availability))) LIKE '%inativ%' "
    "OR LOWER(TRIM(wedrop_status(p.is_active, p.availability))) LIKE '%desativ%' "
    "OR LOWER(TRIM(wedrop_status(p.is_active, p.availability))) LIKE '%inactive%' "
    "OR LOWER(TRIM(wedrop_status(p.is_active, p.availability))) LIKE '%disabled%' "
    "OR LOWER(TRIM(wedrop_status(p.is_active, p.availability))) IN ('false', '0', 'não', 'nao'))"
)

# Nem ativo nem inativo: em geral, página lida antes do selo Disponível/Indisponível aparecer.
_WITHOUT_STATUS_SQL = (
    "(TRIM(wedrop_status(p.is_active, p.availability)) = '' "
    f"OR (NOT {_ACTIVE_SQL} AND NOT {_INACTIVE_SQL} "
    "AND LOWER(TRIM(wedrop_status(p.is_active, p.availability))) NOT LIKE '%active%'))"
)


CATEGORY_COLUMNS = ("category_url", "name", "expected_products", "mapped_products", "updated_at")
STOCK_EVENT_COLUMNS = (
    "event_id",
    "product_id",
    "movement_type",
    "event_kind",
    "quantity",
    "event_at",
    "event_at_raw",
    "nf_key",
    "recorded_at",
)


def _local_timestamp(value: str | None) -> str | None:
    """Converte a data do Supabase (UTC) para o fuso local, como o banco local grava."""
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone().isoformat(timespec="seconds")


def _event_for_dashboard(row: dict[str, Any]) -> dict[str, Any]:
    """Data no fuso local. Movimentações gravadas antes da correção do parser ganham a data do texto original."""
    event_at = _local_timestamp(row.get("event_at")) or (
        (parsed := parse_event_datetime(row.get("event_at_raw") or "")) and parsed.isoformat(timespec="seconds")
    )
    return {**row, "event_at": event_at}


def _local_midnight(day: date) -> str:
    return datetime.combine(day, datetime.min.time()).astimezone().isoformat()


def _day_range(first_day: date, last_day: date) -> tuple[str, str]:
    """Intervalo [início, fim) em horário local, incluindo os dois dias."""
    return _local_midnight(first_day), _local_midnight(last_day + timedelta(days=1))


def _checked_range(start_day: date, end_day: date) -> tuple[str, str]:
    if start_day > end_day:
        raise ValueError("A data inicial deve ser anterior ou igual à data final.")
    return _day_range(start_day, end_day)


class SalesRepository:
    """Lê e grava o histórico local usado pelo dashboard."""

    def __init__(self, database_path: Path | str):
        if str(database_path) != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(database_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.create_function("wedrop_status", 2, effective_status)
        self._create_schema()

    @classmethod
    def from_snapshot(cls, snapshot: dict[str, list[dict[str, Any]]]) -> SalesRepository:
        """Banco em memória com os dados lidos do Supabase, pronto para as mesmas consultas."""
        repository = cls(":memory:")
        categories = [{**row, "updated_at": _local_timestamp(row.get("updated_at"))} for row in snapshot.get("categories", [])]
        products = [{**row, "updated_at": _local_timestamp(row.get("updated_at"))} for row in snapshot.get("products", [])]
        repository._load_rows("categories", CATEGORY_COLUMNS, categories)
        repository._load_rows("products", PRODUCT_FIELDS, products)
        events = [_event_for_dashboard(row) for row in snapshot.get("stock_events", [])]
        repository._load_rows("stock_events", STOCK_EVENT_COLUMNS, events)
        return repository

    def _load_rows(self, table: str, columns: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
        column_list = ", ".join(columns)
        placeholders = ", ".join(f":{column}" for column in columns)
        self.connection.executemany(
            f"INSERT OR REPLACE INTO {table} ({column_list}) VALUES ({placeholders})",
            [{column: row.get(column) for column in columns} for row in rows],
        )
        self.connection.commit()

    def _create_schema(self) -> None:
        self.connection.executescript(_SCHEMA)
        existing_columns = {
            row["name"] for row in self.connection.execute("PRAGMA table_info(products)")
        }
        for column in PRODUCT_DATA_FIELDS:
            if column not in existing_columns:
                self.connection.execute(f"ALTER TABLE products ADD COLUMN {column} TEXT")
        self.connection.commit()

    # ---- gravação ---------------------------------------------------------

    def save_category(self, category: dict[str, Any], mapped_products: int, captured_at: str) -> None:
        self.connection.execute(
            """
            INSERT INTO categories
                (category_url, name, expected_products, mapped_products, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(category_url) DO UPDATE SET
                name = excluded.name,
                expected_products = excluded.expected_products,
                mapped_products = excluded.mapped_products,
                updated_at = excluded.updated_at
            """,
            (category["url"], category["name"], category.get("count"), mapped_products, captured_at),
        )
        self.connection.commit()

    def save_products(self, products: list[dict[str, Any]], captured_at: str) -> None:
        product_values = [
            tuple(product.get(field, "") for field in PRODUCT_DATA_FIELDS) + (captured_at,)
            for product in products
        ]
        columns = ", ".join(PRODUCT_FIELDS)
        placeholders = ", ".join("?" for _ in PRODUCT_FIELDS)
        update_columns = ", ".join(f"{field} = excluded.{field}" for field in PRODUCT_FIELDS[1:])
        self.connection.executemany(
            f"""
            INSERT INTO products ({columns}) VALUES ({placeholders})
            ON CONFLICT(product_id) DO UPDATE SET {update_columns}
            """,
            product_values,
        )
        events = [event for product in products for event in make_event_records(product, captured_at)]
        self.connection.executemany(
            """
            INSERT OR IGNORE INTO stock_events
                (event_id, product_id, movement_type, event_kind, quantity, event_at,
                 event_at_raw, nf_key, recorded_at)
            VALUES (:event_id, :product_id, :movement_type, :event_kind, :quantity,
                    :event_at, :event_at_raw, :nf_key, :recorded_at)
            """,
            events,
        )
        self.connection.commit()

    # ---- consultas do dashboard ------------------------------------------

    def sales_for_day(self, selected_day: date) -> list[sqlite3.Row]:
        start_at, end_at = _day_range(selected_day, selected_day)
        return self._rows(
            """
            SELECT p.product_id, p.name, p.category, p.sku,
                   SUM(e.quantity) AS units_sold,
                   COUNT(e.event_id) AS sale_events
            FROM stock_events AS e
            JOIN products AS p ON p.product_id = e.product_id
            WHERE e.event_kind = 'sale'
              AND e.event_at >= ?
              AND e.event_at < ?
            GROUP BY p.product_id, p.name, p.category, p.sku
            ORDER BY units_sold DESC, p.name COLLATE NOCASE
            LIMIT 20
            """,
            (start_at, end_at),
        )

    def category_activity(self, start_day: date, end_day: date) -> list[sqlite3.Row]:
        start_at, end_at = _checked_range(start_day, end_day)
        return self._rows(
            f"""
            SELECT c.category_url, c.name, c.expected_products, c.mapped_products,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'sale'
                                     THEN e.quantity ELSE 0 END), 0) AS units_sold,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'stock_in'
                                     THEN e.quantity ELSE 0 END), 0) AS units_restocked,
                   COUNT(DISTINCT CASE WHEN {_ACTIVE_SQL} AND NOT {_INACTIVE_SQL}
                                       THEN p.product_id END) AS active_products,
                   COUNT(DISTINCT CASE WHEN {_INACTIVE_SQL}
                                       THEN p.product_id END) AS inactive_products,
                   COUNT(DISTINCT CASE WHEN {_WITHOUT_STATUS_SQL}
                                       THEN p.product_id END) AS products_without_status
            FROM categories AS c
            LEFT JOIN products AS p ON p.category = c.name
            LEFT JOIN stock_events AS e
                   ON e.product_id = p.product_id
                  AND e.event_at >= ?
                  AND e.event_at < ?
            GROUP BY c.category_url, c.name, c.expected_products, c.mapped_products
            ORDER BY c.name COLLATE NOCASE
            """,
            (start_at, end_at),
        )

    def products_for_category_period(
        self, category_name: str, start_day: date, end_day: date
    ) -> list[sqlite3.Row]:
        start_at, end_at = _checked_range(start_day, end_day)
        return self._rows(
            """
            SELECT p.product_id, p.name, p.sku, p.ean, p.url,
                   wedrop_status(p.is_active, p.availability) AS is_active,
                   p.price, p.availability, p.stock, p.total_stock_count,
                   p.real_balance, p.supplier, p.cnpj, p.origin_state, p.ncm,
                   p.weight, p.height, p.width, p.length, p.description,
                   p.number_sales,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'sale'
                                     THEN e.quantity ELSE 0 END), 0) AS units_sold,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'stock_in'
                                     THEN e.quantity ELSE 0 END), 0) AS units_restocked
            FROM products AS p
            LEFT JOIN stock_events AS e
                   ON e.product_id = p.product_id
                  AND e.event_at >= ?
                  AND e.event_at < ?
            WHERE p.category = ?
            GROUP BY p.product_id, p.name, p.sku, p.ean, p.url,
                     wedrop_status(p.is_active, p.availability),
                     p.price, p.availability, p.stock, p.total_stock_count,
                     p.real_balance, p.supplier, p.cnpj, p.origin_state, p.ncm,
                     p.weight, p.height, p.width, p.length, p.description,
                     p.number_sales
            ORDER BY units_sold DESC, units_restocked DESC,
                     p.name COLLATE NOCASE
            """,
            (start_at, end_at, category_name),
        )

    def products_activity_for_category(
        self, category_name: str, start_day: date, end_day: date
    ) -> list[sqlite3.Row]:
        start_at, end_at = _checked_range(start_day, end_day)
        return self._rows(
            """
            SELECT p.product_id, p.name, p.sku, p.stock, p.real_balance,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'sale'
                                     THEN e.quantity ELSE 0 END), 0) AS units_sold,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'stock_in'
                                     THEN e.quantity ELSE 0 END), 0) AS units_restocked,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'sale'
                                     THEN 1 ELSE 0 END), 0) AS sale_events,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'stock_in'
                                     THEN 1 ELSE 0 END), 0) AS restock_events
            FROM products AS p
            LEFT JOIN stock_events AS e
                   ON e.product_id = p.product_id
                  AND e.event_at >= ?
                  AND e.event_at < ?
            WHERE p.category = ?
            GROUP BY p.product_id, p.name, p.sku, p.stock, p.real_balance
            HAVING SUM(CASE WHEN e.event_kind IN ('sale', 'stock_in')
                            THEN e.quantity ELSE 0 END) > 0
            ORDER BY units_sold DESC, units_restocked DESC, p.name COLLATE NOCASE
            """,
            (start_at, end_at, category_name),
        )

    def category_daily_activity(
        self, start_day: date, end_day: date, category_name: str | None = None
    ) -> list[sqlite3.Row]:
        start_at, end_at = _checked_range(start_day, end_day)
        params: list[Any] = [start_at, end_at]
        category_filter = ""
        if category_name is not None:
            category_filter = "AND p.category = ?"
            params.append(category_name)
        return self._rows(
            f"""
            SELECT substr(e.event_at, 1, 10) AS day,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'sale'
                                     THEN e.quantity ELSE 0 END), 0) AS units_sold,
                   COALESCE(SUM(CASE WHEN e.event_kind = 'stock_in'
                                     THEN e.quantity ELSE 0 END), 0) AS units_restocked
            FROM stock_events AS e
            JOIN products AS p ON p.product_id = e.product_id
            WHERE e.event_at >= ? AND e.event_at < ?
              AND e.event_kind IN ('sale', 'stock_in')
              {category_filter}
            GROUP BY substr(e.event_at, 1, 10)
            ORDER BY day
            """,
            params,
        )

    def top_products_daily_activity(
        self,
        start_day: date,
        end_day: date,
        category_name: str | None = None,
        limit: int = 100,
    ) -> list[sqlite3.Row]:
        """Vendas e reposições por dia dos produtos que mais movimentaram no período."""
        start_at, end_at = _checked_range(start_day, end_day)
        params: list[Any] = [start_at, end_at]
        category_filter = ""
        if category_name is not None:
            category_filter = "AND p.category = ?"
            params.append(category_name)
        params.append(limit)
        return self._rows(
            f"""
            WITH moves AS (
                SELECT e.product_id, substr(e.event_at, 1, 10) AS day,
                       SUM(CASE WHEN e.event_kind = 'sale'
                                THEN e.quantity ELSE 0 END) AS units_sold,
                       SUM(CASE WHEN e.event_kind = 'stock_in'
                                THEN e.quantity ELSE 0 END) AS units_restocked
                FROM stock_events AS e
                JOIN products AS p ON p.product_id = e.product_id
                WHERE e.event_at >= ? AND e.event_at < ?
                  AND e.event_kind IN ('sale', 'stock_in')
                  {category_filter}
                GROUP BY e.product_id, substr(e.event_at, 1, 10)
            ),
            ranked AS (
                SELECT product_id, SUM(units_sold) AS total_sold,
                       SUM(units_restocked) AS total_restocked
                FROM moves
                GROUP BY product_id
                HAVING SUM(units_sold) + SUM(units_restocked) > 0
                ORDER BY total_sold DESC, total_restocked DESC
                LIMIT ?
            )
            SELECT p.product_id, p.name, p.category, p.url, m.day,
                   m.units_sold, m.units_restocked, r.total_sold, r.total_restocked
            FROM ranked AS r
            JOIN moves AS m ON m.product_id = r.product_id
            JOIN products AS p ON p.product_id = r.product_id
            ORDER BY r.total_sold DESC, r.total_restocked DESC,
                     p.name COLLATE NOCASE, m.day
            """,
            params,
        )

    def top_products_for_period(self, start_day: date, end_day: date) -> list[sqlite3.Row]:
        start_at, end_at = _checked_range(start_day, end_day)
        return self._rows(
            """
            SELECT p.product_id, p.name, p.category, p.sku, p.url,
                   SUM(e.quantity) AS units_sold
            FROM stock_events AS e
            JOIN products AS p ON p.product_id = e.product_id
            WHERE e.event_kind = 'sale'
              AND e.event_at >= ?
              AND e.event_at < ?
            GROUP BY p.product_id, p.name, p.category, p.sku
            ORDER BY units_sold DESC, p.name COLLATE NOCASE
            LIMIT 20
            """,
            (start_at, end_at),
        )

    def daily_sales(self, through_day: date, days: int = 14) -> list[sqlite3.Row]:
        first_day = through_day - timedelta(days=days - 1)
        start_at, end_at = _day_range(first_day, through_day)
        return self._rows(
            """
            SELECT substr(event_at, 1, 10) AS day, SUM(quantity) AS units_sold
            FROM stock_events
            WHERE event_kind = 'sale'
              AND event_at >= ?
              AND event_at < ?
            GROUP BY substr(event_at, 1, 10)
            ORDER BY day
            """,
            (start_at, end_at),
        )

    def stock_entries_for_day(self, selected_day: date) -> list[sqlite3.Row]:
        start_at, end_at = _day_range(selected_day, selected_day)
        return self._rows(
            """
            SELECT p.name, p.category, e.quantity, e.event_at, e.movement_type
            FROM stock_events AS e
            JOIN products AS p ON p.product_id = e.product_id
            WHERE e.event_kind = 'stock_in'
              AND e.event_at >= ?
              AND e.event_at < ?
            ORDER BY e.event_at DESC
            """,
            (start_at, end_at),
        )

    def products_without_status(self) -> list[sqlite3.Row]:
        """Produtos sem status ativo/inativo, para conferir no painel."""
        return self._rows(
            f"""
            SELECT p.product_id, p.name, p.category, p.url, p.supplier, p.stock, p.updated_at
            FROM products AS p
            WHERE {_WITHOUT_STATUS_SQL}
            ORDER BY p.category COLLATE NOCASE, p.product_id
            """
        )

    def product_count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM products").fetchone()[0])

    def categories(self) -> list[sqlite3.Row]:
        return self._rows(
            """
            SELECT name, expected_products, mapped_products, updated_at
            FROM categories
            ORDER BY name COLLATE NOCASE
            """
        )

    def category_baselines(self) -> dict[str, int | None]:
        """Quantidade de produtos informada pelo site em cada categoria na última coleta."""
        return {row["name"]: row["expected_products"] for row in self.categories()}

    def _rows(self, sql: str, params: tuple | list = ()) -> list[sqlite3.Row]:
        return list(self.connection.execute(sql, params))

    def close(self) -> None:
        self.connection.close()
