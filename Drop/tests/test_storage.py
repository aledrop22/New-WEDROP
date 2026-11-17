"""Persistência: SQLite do dashboard, Supabase e movimentações de estoque."""

import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import requests

from wedrop.storage.sqlite_repository import SalesRepository
from wedrop.storage.stock_events import (
    classify_movement,
    make_stock_snapshot,
    parse_event_datetime,
    parse_quantity,
)
from wedrop.storage.supabase_repository import SupabaseRepository


class StorageTests(unittest.TestCase):
    def test_supabase_outbox_survives_reopen_until_upload_is_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "report.db"
            repository = SalesRepository(database)
            repository.enqueue_supabase_products(
                [{"product_id": "123", "name": "Produto teste"}],
                "2026-11-05T06:00:00-03:00",
            )
            repository.enqueue_supabase_category(
                {"name": "Casa", "url": "https://example.com/casa", "count": 1},
                1,
                "2026-11-05T06:00:00-03:00",
            )
            first = repository.pending_supabase_uploads()
            repository.close()

            repository = SalesRepository(database)
            pending = repository.pending_supabase_uploads()
            self.assertEqual(pending, first)
            self.assertEqual([item["kind"] for item in pending], ["products", "category"])
            repository.remove_supabase_upload(pending[0]["id"])
            self.assertEqual(
                [item["kind"] for item in repository.pending_supabase_uploads()],
                ["category"],
            )
            repository.close()

    def test_parses_date_formats_and_quantities(self):
        for value in ("10/10/2026 15:42:08", "2026-10-10T15:42:08"):
            parsed = parse_event_datetime(value)
            self.assertIsNotNone(parsed)
            if parsed is not None:
                self.assertEqual(parsed.strftime("%Y-%m-%dT%H:%M:%S"), "2026-10-10T15:42:08")
        # parse_quantity retorna valor absoluto (sem sinal)
        self.assertEqual(parse_quantity("-12 unidades"), 12)
        self.assertEqual(parse_quantity("+526 unidades"), 526)
        self.assertIsNone(parse_event_datetime("data indisponível"))

    def test_classifies_sales_and_stock_entries(self):
        self.assertEqual(classify_movement("Saída"), "sale")
        self.assertEqual(classify_movement("Venda"), "sale")
        self.assertEqual(classify_movement("Entrada de estoque"), "stock_in")
        self.assertEqual(classify_movement("Ajuste manual"), "other")

    def test_stock_snapshot_is_deduplicated_and_keeps_listing_state(self):
        product = {
            "product_id": "p1",
            "availability": "Indisponível",
            "is_active": "Inativo",
            "stock": "0",
            "real_balance": "0",
        }
        first = make_stock_snapshot(product, "2026-11-09T10:00:00-03:00", False)
        second = make_stock_snapshot(product, "2026-11-09T10:00:00-03:00", False)
        self.assertEqual(first, second)
        self.assertFalse(first["is_listed"])
        self.assertEqual(first["stock"], "0")

    def test_stock_snapshot_storage_prunes_rows_older_than_seven_days(self):
        repository = SalesRepository(":memory:")
        self.addCleanup(repository.close)
        repository.save_products(
            [{"product_id": "p1", "name": "Produto", "category": "Casa", "url": "https://x/p1"}],
            "2026-11-09T10:00:00-03:00",
        )
        old_snapshot = make_stock_snapshot(
            {"product_id": "p1", "stock": "4"},
            "2026-11-01T10:00:00-03:00",
        )
        recent_snapshot = make_stock_snapshot(
            {"product_id": "p1", "stock": "0"},
            "2026-11-09T10:00:00-03:00",
        )
        repository.save_stock_snapshots([old_snapshot])
        repository.save_stock_snapshots([recent_snapshot])
        rows = repository.connection.execute(
            "SELECT observation_id, stock FROM stock_snapshots"
        ).fetchall()
        self.assertEqual([tuple(row) for row in rows], [(recent_snapshot["observation_id"], "0")])

    def test_repeated_daily_scan_does_not_duplicate_sales(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        repository = SalesRepository(Path(temp_dir) / "report.db")
        self.addCleanup(repository.close)
        product = {
            "product_id": "123",
            "name": "Produto teste",
            "category": "Categoria teste",
            "url": "https://dash.wedrop.com.br/catalog/123",
            "sku": "SKU-123",
            "stock": "15",
            "real_balance": "12",
            "description": "Descrição do produto",
            "stock_history": [
                {
                    "type": "Saída",
                    "quantity": "-2",
                    "date": "10/10/2026 15:42:08",
                },
                {
                    "type": "Entrada",
                    "quantity": "+5",
                    "date": "10/10/2026 15:43:08",
                },
            ],
        }
        repository.save_products([product], "2026-10-10T16:00:00")
        repository.save_products([product], "2026-10-11T16:00:00")

        sales = repository.sales_for_day(date(2026, 10, 10))
        entries = repository.stock_entries_for_day(date(2026, 10, 10))
        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0]["units_sold"], 2)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["quantity"], 5)
        saved_product = repository.connection.execute(
            "SELECT sku, stock, real_balance, description, first_seen_at FROM products"
        ).fetchone()
        self.assertEqual(
            tuple(saved_product),
            ("SKU-123", "15", "12", "Descrição do produto", "2026-10-10T16:00:00"),
        )

    def test_existing_product_without_first_seen_stays_in_baseline(self):
        repository = SalesRepository(":memory:")
        self.addCleanup(repository.close)
        product = {
            "product_id": "existing",
            "name": "Produto da base",
            "category": "Casa",
            "url": "https://example.com/products/existing",
        }
        repository.save_products([product], "2026-10-10T12:00:00")
        repository.connection.execute(
            "UPDATE products SET first_seen_at = NULL WHERE product_id = ?",
            ("existing",),
        )
        repository.connection.commit()

        repository.save_products([product], "2026-10-11T12:00:00")
        repository.save_products(
            [{**product, "product_id": "new", "name": "Produto novo"}],
            "2026-10-11T12:00:00",
        )

        first_seen = dict(
            repository.connection.execute(
                "SELECT product_id, first_seen_at FROM products"
            ).fetchall()
        )
        self.assertIsNone(first_seen["existing"])
        self.assertEqual(first_seen["new"], "2026-10-11T12:00:00")

    def test_period_activity_aggregates_inclusive_dates_by_category_and_product(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        repository = SalesRepository(Path(temp_dir) / "report.db")
        self.addCleanup(repository.close)
        self.addCleanup(repository.close)
        repository.save_category(
            {"url": "https://example.com/cat/a", "name": "Categoria A"},
            2,
            "2026-10-12T12:00:00",
        )
        repository.save_category(
                {"url": "https://example.com/cat/b", "name": "Categoria B"},
                0,
                "2026-10-12T12:00:00",
            )
        repository.save_products(
                [
                    {
                        "product_id": "a1",
                        "name": "Produto A1",
                        "category": "Categoria A",
                        "url": "https://example.com/products/a1",
                        "sku": "A1",
                        "ean": "789123",
                        "price": "R$ 10,00",
                        "description": "Descrição de teste",
                        "ncm": "12345678",
                        "is_active": "Ativo",
                        "stock_history": [
                            {
                                "type": "Venda",
                                "quantity": "-2",
                                "date": "10/10/2026 00:00:00",
                            },
                            {
                                "type": "Entrada",
                                "quantity": "+5",
                                "date": "11/10/2026 23:59:59",
                            },
                            {
                                "type": "Venda",
                                "quantity": "-3",
                                "date": "12/10/2026 23:59:59",
                            },
                        ],
                    },
                    {
                        "product_id": "a2",
                        "name": "Produto A2",
                        "category": "Categoria A",
                        "url": "https://example.com/products/a2",
                        "sku": "A2",
                        "is_active": "Inativo",
                        "stock_history": [
                            {
                                "type": "Venda",
                                "quantity": "-4",
                                "date": "11/10/2026 12:00:00",
                            }
                        ],
                    },
                    {
                        "product_id": "b1",
                        "name": "Produto B1",
                        "category": "Categoria B",
                        "url": "https://example.com/products/b1",
                        "is_active": "Ativo",
                        "stock_history": [
                            {
                                "type": "Venda",
                                "quantity": "-8",
                                "date": "11/10/2026 12:00:00",
                            }
                        ],
                    },
                ],
                "2026-10-13T12:00:00",
            )

        categories = {
                row["name"]: row
                for row in repository.category_activity(
                    date(2026, 10, 10), date(2026, 10, 12)
                )
            }
        self.assertEqual(categories["Categoria A"]["units_sold"], 9)
        self.assertEqual(categories["Categoria A"]["units_restocked"], 5)
        self.assertEqual(categories["Categoria A"]["active_products"], 1)
        self.assertEqual(categories["Categoria A"]["inactive_products"], 1)
        self.assertEqual(categories["Categoria A"]["products_without_status"], 0)
        self.assertEqual(categories["Categoria B"]["units_sold"], 8)

        category_products = repository.products_for_category_period(
            "Categoria A", date(2026, 10, 10), date(2026, 10, 12)
        )
        self.assertEqual(
            [(row["name"], row["is_active"]) for row in category_products],
            [("Produto A1", "Ativo"), ("Produto A2", "Inativo")],
        )
        self.assertEqual(category_products[0]["price"], "R$ 10,00")
        self.assertEqual(category_products[0]["description"], "Descrição de teste")
        self.assertEqual(category_products[0]["ncm"], "12345678")

        products = repository.products_activity_for_category(
            "Categoria A", date(2026, 10, 10), date(2026, 10, 12)
        )
        self.assertEqual(
            [(row["name"], row["units_sold"], row["units_restocked"]) for row in products],
            [("Produto A1", 5, 5), ("Produto A2", 4, 0)],
        )

        daily = repository.category_daily_activity(
            date(2026, 10, 10), date(2026, 10, 12), "Categoria A"
        )
        self.assertEqual(
            [(row["day"], row["units_sold"], row["units_restocked"]) for row in daily],
            [("2026-10-10", 2, 0), ("2026-10-11", 4, 5), ("2026-10-12", 3, 0)],
        )
        top_daily = repository.top_products_daily_activity(
            date(2026, 10, 10), date(2026, 10, 12), "Categoria A", limit=1
        )
        self.assertEqual({row["name"] for row in top_daily}, {"Produto A1"})
        self.assertEqual(sum(row["units_sold"] for row in top_daily), 5)
        self.assertEqual(
            repository.top_products_for_period(
                date(2026, 10, 10), date(2026, 10, 12)
            )[0]["name"],
            "Produto B1",
        )
        self.assertEqual(
            repository.top_products_for_period(
                date(2026, 10, 10), date(2026, 10, 12)
            )[0]["url"],
            "https://example.com/products/b1",
        )

    def test_period_activity_rejects_reversed_dates(self):
        temp_dir = self.enterContext(tempfile.TemporaryDirectory())
        repository = SalesRepository(Path(temp_dir) / "report.db")
        self.addCleanup(repository.close)
        self.addCleanup(repository.close)
        with self.assertRaisesRegex(ValueError, "data inicial"):
            repository.category_activity(date(2026, 10, 12), date(2026, 10, 10))

    def test_existing_product_database_is_upgraded_without_losing_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "report.db"
            connection = sqlite3.connect(database_path)
            connection.execute(
                """
                CREATE TABLE products (
                    product_id TEXT PRIMARY KEY, name TEXT NOT NULL,
                    category TEXT NOT NULL, url TEXT NOT NULL, sku TEXT,
                    price TEXT, stock TEXT, updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO products VALUES ('1', 'Existing', 'Cat', 'url', '', '', '', 'today')"
            )
            connection.commit()
            connection.close()

            repository = SalesRepository(database_path)
            columns = {
                row["name"]
                for row in repository.connection.execute("PRAGMA table_info(products)")
            }
            self.assertIn("real_balance", columns)
            self.assertEqual(
                repository.connection.execute(
                    "SELECT name FROM products WHERE product_id='1'"
                ).fetchone()["name"],
                "Existing",
            )
            repository.close()

    def test_supabase_requires_configuration_and_reports_upsert_errors(self):
        with patch("wedrop.storage.supabase_repository.load_environment"):
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "Supabase não configurado"):
                    SupabaseRepository.from_environment()

        failed_response = Mock(spec=requests.Response)
        failed_response.ok = False
        failed_response.status_code = 401
        failed_response.text = "Unauthorized"
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        with patch.object(repository.session, "post", return_value=failed_response):
            with self.assertRaisesRegex(RuntimeError, "HTTP 401"):
                repository._upsert(
                    "wedrop_products", [{"product_id": "1"}], "product_id"
                )
        repository.close()

    def test_supabase_retries_temporary_connection_failure(self):
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        successful_response = Mock(spec=requests.Response)
        successful_response.ok = True
        with patch.object(
            repository.session,
            "post",
            side_effect=[
                requests.exceptions.SSLError("temporary EOF"),
                successful_response,
            ],
        ) as post:
            with patch("wedrop.storage.supabase_repository.time.sleep") as sleep:
                repository._upsert(
                    "wedrop_products", [{"product_id": "1"}], "product_id"
                )
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1)
        repository.close()

    def test_supabase_retries_temporary_http_failure(self):
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        unavailable_response = Mock(spec=requests.Response)
        unavailable_response.ok = False
        unavailable_response.status_code = 503
        unavailable_response.text = "Service unavailable"
        successful_response = Mock(spec=requests.Response)
        successful_response.ok = True
        with patch.object(
            repository.session,
            "post",
            side_effect=[unavailable_response, successful_response],
        ) as post:
            with patch("wedrop.storage.supabase_repository.time.sleep") as sleep:
                repository._upsert(
                    "wedrop_products", [{"product_id": "1"}], "product_id"
                )
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(1)
        repository.close()

    def test_supabase_retries_first_seen_query_after_connection_error(self):
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        successful_response = Mock(spec=requests.Response)
        successful_response.ok = True
        successful_response.json.return_value = [
            {"product_id": "1", "first_seen_at": "2026-10-01T12:00:00+00:00"}
        ]
        with patch.object(
            repository.session,
            "get",
            side_effect=[requests.ConnectionError("remote disconnected"), successful_response],
        ) as get:
            with patch("wedrop.storage.supabase_repository.time.sleep") as sleep:
                result = repository._fetch_first_seen_at(["1"])

        self.assertEqual(
            result, {"1": "2026-10-01T12:00:00+00:00"}
        )
        self.assertEqual(get.call_count, 2)
        sleep.assert_called_once_with(1)
        repository.close()

    def test_supabase_validates_all_required_tables_before_scraping(self):
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        successful_response = Mock(spec=requests.Response)
        successful_response.ok = True
        with patch.object(
            repository.session, "get", return_value=successful_response
        ) as get:
            repository.validate()
        # quatro tabelas e as colunas price_changed_at e first_seen_at de wedrop_products
        self.assertEqual(get.call_count, 6)

        failed_response = Mock(spec=requests.Response)
        failed_response.ok = False
        failed_response.status_code = 404
        failed_response.text = "table missing"
        with patch.object(repository.session, "get", return_value=failed_response):
            with self.assertRaisesRegex(RuntimeError, "wedrop_categories"):
                repository.validate()
        repository.close()

    def test_supabase_upserts_full_product_and_deduplicated_history(self):
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        successful_response = Mock(spec=requests.Response)
        successful_response.ok = True
        existing_products_response = Mock(spec=requests.Response)
        existing_products_response.ok = True
        existing_products_response.json.return_value = [
            {"product_id": "321", "first_seen_at": "2026-10-01T12:00:00+00:00"},
            {"product_id": "654", "first_seen_at": None},
        ]
        product = {
            "product_id": "321",
            "name": "Produto",
            "category": "Casa",
            "url": "https://example.com/catalog/321",
            "stock": "4",
            "real_balance": "3",
            "stock_history": [
                {
                    "type": "Saída",
                    "quantity": "-1",
                    "date": "10/10/2026 12:00:00",
                }
            ],
        }
        with patch.object(
            repository.session, "get", return_value=existing_products_response
        ):
            with patch.object(
                repository.session, "post", return_value=successful_response
            ) as post:
                repository.save_products([product, product], "2026-10-10T15:00:00-03:00")
        self.assertEqual(post.call_count, 2)
        product_payload = post.call_args_list[0].kwargs["json"]
        history_payload = post.call_args_list[1].kwargs["json"]
        self.assertEqual(len(product_payload), 2)
        self.assertEqual(product_payload[0]["real_balance"], "3")
        self.assertEqual(product_payload[0]["first_seen_at"], "2026-10-01T12:00:00+00:00")
        self.assertEqual(len(history_payload), 1)
        self.assertEqual(history_payload[0]["event_kind"], "sale")
        repository.close()

    def test_supabase_preserves_baseline_null_and_dates_new_product(self):
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        existing_response = Mock(spec=requests.Response)
        existing_response.ok = True
        existing_response.json.return_value = [
            {"product_id": "old", "first_seen_at": None}
        ]
        successful_response = Mock(spec=requests.Response)
        successful_response.ok = True
        products = [
            {
                "product_id": product_id,
                "name": product_id,
                "category": "Casa",
                "url": f"https://example.com/products/{product_id}",
            }
            for product_id in ("old", "new")
        ]

        with patch.object(repository.session, "get", return_value=existing_response):
            with patch.object(
                repository.session, "post", return_value=successful_response
            ) as post:
                repository.save_products(products, "2026-10-11T12:00:00+00:00")

        payload = post.call_args_list[0].kwargs["json"]
        first_seen_by_id = {
            row["product_id"]: row["first_seen_at"] for row in payload
        }
        self.assertIsNone(first_seen_by_id["old"])
        self.assertEqual(
            first_seen_by_id["new"], "2026-10-11T12:00:00+00:00"
        )
        repository.close()
