"""Coleta diária incremental: decisão por categoria, troca de registros e leitura de preço e saldo."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from wedrop.mapping import MappingSummary, _full_read_reason, _ProductsJsonFile, _refresh_category
from wedrop.scraping.catalog import Category
from wedrop.scraping.product_page import ProductJob
from wedrop.scraping.product_record import (
    PRICE_CHANGED,
    STOCK_CHANGED,
    UNCHANGED,
    PageSnapshot,
    build_balance_update,
    compare_balance,
    fill_from_known,
)
from wedrop.storage import products_file
from wedrop.storage.sqlite_repository import SalesRepository

COZINHA = Category("Cozinha", "https://x/cozinha", 1276)


class ReadDecisionTests(unittest.TestCase):
    def test_category_never_collected_is_read_in_full(self):
        self.assertEqual(_full_read_reason(COZINHA, {}, 0), "categoria ainda não coletada")

    def test_changed_count_is_read_in_full(self):
        reason = _full_read_reason(COZINHA, {"Cozinha": 1270}, 1270)
        self.assertEqual(reason, "quantidade mudou de 1270 para 1276")

    def test_missing_products_in_products_file_are_read_in_full(self):
        reason = _full_read_reason(COZINHA, {"Cozinha": 1276}, 1200)
        self.assertEqual(reason, "o data.json tem 1200 de 1276 produtos")

    def test_unchanged_category_needs_only_price_and_balance(self):
        self.assertIsNone(_full_read_reason(COZINHA, {"Cozinha": 1276}, 1276))

    def test_site_without_count_is_read_in_full(self):
        category = Category("Cozinha", "https://x/cozinha", None)
        self.assertIsNotNone(_full_read_reason(category, {"Cozinha": None}, 10))


class BalanceUpdateTests(unittest.TestCase):
    def setUp(self):
        self.known = {
            "price": "R$ 10,00",
            "stock": "3 un.",
            "stock_history": [
                {"type": "Saldo inicial", "quantity": "10"},
                {"type": "ENTRADA", "quantity": "+ 5"},
                {"type": "SAÍDA", "quantity": "- 3"},
            ],
        }

    def test_price_and_stock_come_from_the_page_and_balance_uses_stored_history(self):
        snapshot = PageSnapshot(
            body_text="Cozinha",
            price_candidates=("R$ 49,90",),
            stock_candidates=("11 un.",),
        )
        update = build_balance_update(self.known, snapshot)
        self.assertEqual(update["price"], "R$ 49,90")
        self.assertEqual(update["stock"], "11 un.")
        self.assertEqual(update["real_balance"], "12")
        self.assertEqual(update["total_stock_count"], "12")

    def test_missing_price_keeps_the_stored_price(self):
        update = build_balance_update(self.known, PageSnapshot(body_text=""))
        self.assertEqual(update["price"], "R$ 10,00")


class CompareWithPreviousDayTests(unittest.TestCase):
    known = {"price": "R$ 10,00", "stock": "3 un."}

    def test_same_price_and_stock_is_unchanged(self):
        self.assertEqual(compare_balance(self.known, {"price": "R$ 10,00", "stock": "3 un."}), UNCHANGED)

    def test_only_price_changed(self):
        self.assertEqual(compare_balance(self.known, {"price": "R$ 12,00", "stock": "3 un."}), PRICE_CHANGED)

    def test_stock_change_wins_over_price_change(self):
        self.assertEqual(compare_balance(self.known, {"price": "R$ 12,00", "stock": "2 un."}), STOCK_CHANGED)

    def test_reread_keeps_previous_value_of_fields_left_empty(self):
        record = {"price": "R$ 12,00", "cnpj": "", "stock": "2 un."}
        merged = fill_from_known(record, {"price": "R$ 10,00", "cnpj": "12.345.678/0001-90", "stock": "3 un."})
        self.assertEqual(merged, {"price": "R$ 12,00", "cnpj": "12.345.678/0001-90", "stock": "2 un."})


class ProductsJsonFileTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "data.json"
        lines = [
            {"product_id": "1", "category": "Cozinha", "price": "10", "url": "u1"},
            {"product_id": "2", "category": "Casa", "price": "20", "url": "u2"},
        ]
        self.path.write_text(
            "\n".join([json.dumps(lines[0]), "linha quebrada", json.dumps(lines[1])]) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self._temp.cleanup()

    def test_groups_stored_products_by_category(self):
        grouped = _ProductsJsonFile(self.path).by_category()
        self.assertEqual([record["product_id"] for record in grouped["Cozinha"]], ["1"])
        self.assertEqual([record["product_id"] for record in grouped["Casa"]], ["2"])

    def test_upsert_replaces_in_place_and_appends_new_products(self):
        products_json = _ProductsJsonFile(self.path)
        products_json.upsert([
            {"product_id": "1", "category": "Cozinha", "price": "12"},
            {"product_id": "3", "category": "Cozinha", "price": "5"},
        ])
        products_json.save()

        records = products_file.read_records(self.path)
        self.assertEqual(records[0], {"product_id": "1", "category": "Cozinha", "price": "12"})
        self.assertEqual(records[1], "linha quebrada")
        self.assertEqual(records[2]["product_id"], "2")
        self.assertEqual(records[3]["product_id"], "3")

    def test_products_no_longer_listed_in_category_are_removed(self):
        products_json = _ProductsJsonFile(self.path)
        products_json.upsert([{"product_id": "3", "category": "Cozinha", "price": "5"}])
        removed = products_json.remove_missing("Cozinha", {"1"})
        products_json.save()

        self.assertEqual(removed, ["3"])
        ids = [record["product_id"] for record in products_file.read_records(self.path) if isinstance(record, dict)]
        self.assertEqual(ids, ["1", "2"])


class FakeCrawler:
    """Registra as leituras pedidas; cada chamada falha nos IDs indicados em `failures_per_call`."""

    def __init__(self, failures_per_call=()):
        self.calls: list[list[ProductJob]] = []
        self._failures = list(failures_per_call)

    async def crawl(self, jobs):
        self.calls.append(jobs)
        failing = self._failures.pop(0) if self._failures else set()
        return [(job, RuntimeError("falha simulada")) for job in jobs if job.product_id in failing]


class RefreshCategoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        folder = Path(self._temp.name)
        self.repository = SalesRepository(folder / "banco.db")
        # Última coleta: 1 produto; o site agora informa 2.
        self.repository.save_category({"url": COZINHA.url, "name": "Cozinha", "count": 1}, 1, "2026-10-12T10:00:00-03:00")
        self.path = folder / "data.json"
        self.path.write_text(
            "\n".join(
                json.dumps(record)
                for record in (
                    {"product_id": "1", "category": "Cozinha", "price": "10", "url": "https://x/catalog/1", "stock_history": []},
                    {"product_id": "2", "category": "Cozinha", "price": "20", "url": "https://x/catalog/2", "stock_history": []},
                    {"product_id": "3", "category": "Casa", "price": "30", "url": "https://x/catalog/3", "stock_history": []},
                )
            )
            + "\n",
            encoding="utf-8",
        )
        self.products_json = _ProductsJsonFile(self.path)

    def tearDown(self):
        self.repository.close()
        self._temp.cleanup()

    async def _refresh(self, count, baseline, listing=None, failures_per_call=(), shortfall=False):
        category = Category("Cozinha", COZINHA.url, count)
        known = self.products_json.by_category().get("Cozinha", [])
        summary = MappingSummary()
        crawler = FakeCrawler(failures_per_call)

        async def fake_listing(_page, _category, current_summary):
            if shortfall:
                current_summary.shortfall_categories.append("Cozinha")
            return listing or {}

        with patch("wedrop.mapping._read_listing", new=fake_listing):
            await _refresh_category(
                "[1/1] Cozinha",
                category,
                {"Cozinha": baseline},
                known,
                None,
                crawler,
                self.products_json,
                self.repository,
                None,
                "2026-10-13T10:00:00-03:00",
                summary,
            )
        return summary, crawler

    async def test_unchanged_category_reads_only_stored_products_without_listing(self):
        summary, crawler = await self._refresh(count=2, baseline=2)

        self.assertEqual(summary.balance_only_categories, ["Cozinha"])
        self.assertEqual(summary.full_categories, [])
        self.assertEqual([job.product_id for job in crawler.calls[0]], ["1", "2"])
        self.assertTrue(all(job.known_record is not None for job in crawler.calls[0]))
        self.assertEqual(self.repository.category_baselines(), {"Cozinha": 2})

    async def test_changed_category_is_read_in_full_and_products_gone_from_site_are_removed(self):
        listing = {"1": "https://x/catalog/1", "9": "https://x/catalog/9"}
        summary, crawler = await self._refresh(count=2, baseline=1, listing=listing)

        self.assertEqual(summary.full_categories, ["Cozinha"])
        self.assertEqual(summary.balance_only_categories, [])
        self.assertEqual([job.product_id for job in crawler.calls[0]], ["1", "9"])
        self.assertTrue(all(job.known_record is None for job in crawler.calls[0]))
        stored_ids = sorted(record["product_id"] for record in self.products_json.by_category()["Cozinha"])
        self.assertEqual(stored_ids, ["1"])
        self.assertEqual(self.repository.category_baselines(), {"Cozinha": 2})

    async def test_failed_balance_read_falls_back_to_full_category(self):
        listing = {"1": "https://x/catalog/1", "2": "https://x/catalog/2"}
        summary, crawler = await self._refresh(
            count=2, baseline=2, listing=listing, failures_per_call=[{"2"}, set()]
        )

        self.assertEqual(summary.balance_only_categories, [])
        self.assertEqual(summary.full_categories, ["Cozinha"])
        self.assertEqual(len(crawler.calls), 2)
        self.assertEqual([job.product_id for job in crawler.calls[1]], ["1", "2"])
        self.assertEqual(summary.failed_ids, [])
        self.assertEqual(self.repository.category_baselines(), {"Cozinha": 2})

    async def test_incomplete_listing_keeps_old_baseline_so_next_run_reads_again(self):
        listing = {"1": "https://x/catalog/1"}
        summary, _ = await self._refresh(count=2, baseline=1, listing=listing, shortfall=True)

        self.assertEqual(summary.full_categories, ["Cozinha"])
        self.assertEqual(self.repository.category_baselines(), {"Cozinha": 1})
        self.assertFalse(summary.is_complete)


class BaselineTests(unittest.TestCase):
    def test_last_saved_count_per_category_is_the_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            repository = SalesRepository(Path(folder) / "banco.db")
            try:
                self.assertEqual(repository.category_baselines(), {})
                repository.save_category({"url": COZINHA.url, "name": "Cozinha", "count": 1276}, 1276, "2026-10-12T10:00:00-03:00")
                self.assertEqual(repository.category_baselines(), {"Cozinha": 1276})
            finally:
                repository.close()


if __name__ == "__main__":
    unittest.main()
