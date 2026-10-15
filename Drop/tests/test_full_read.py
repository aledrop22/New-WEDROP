"""Quando a categoria inteira precisa ser lida (e quando basta preço e saldo)."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import Mock

from wedrop.mapping import MappingSummary, _full_read_reason, _refresh_category
from wedrop.scraping.catalog import Category
from wedrop.scraping.product_page import ProductJob


def _category(count: int | None) -> Category:
    return Category(name="Cozinha", url="https://example.com/cozinha", count=count)


def _record(product_id: str, status: str = "Ativo") -> dict:
    return {
        "product_id": product_id,
        "name": f"Produto {product_id}",
        "category": "Cozinha",
        "url": f"https://example.com/catalog/{product_id}",
        "is_active": status,
        "price": "R$ 10,00",
        "stock": "5",
    }


class FakeCrawler:
    """Devolve, a cada chamada, a próxima lista de falhas programada."""

    def __init__(self, results: list[list]):
        self._results = list(results)
        self.calls: list[list] = []

    async def crawl(self, jobs):
        self.calls.append(jobs)
        return self._results.pop(0)


class FullReadReasonTest(unittest.TestCase):
    def test_same_total_with_sold_out_products_is_balance_only(self):
        # 1276 produtos guardados (inclusive os esgotados) e 1276 no site: só preço e saldo
        self.assertIsNone(_full_read_reason(_category(1276), {"Cozinha": 1276}, 1276))

    def test_count_change_is_full_read(self):
        reason = _full_read_reason(_category(1277), {"Cozinha": 1276}, 1276)
        self.assertIn("quantidade mudou", reason)

    def test_missing_products_in_data_is_full_read(self):
        reason = _full_read_reason(_category(1276), {"Cozinha": 1276}, 1200)
        self.assertIn("1200 de 1276", reason)

    def test_new_category_is_full_read(self):
        self.assertIn("ainda não coletada", _full_read_reason(_category(10), {}, 0))


class BalanceFailuresTest(unittest.TestCase):
    def _run(self, crawler: FakeCrawler, known: list[dict]) -> MappingSummary:
        summary = MappingSummary()
        category = _category(len(known))
        asyncio.run(
            _refresh_category(
                "[1/1] Cozinha",
                category,
                {"Cozinha": len(known)},
                known,
                listing_page=None,  # não deve ser usada: leitura completa não pode acontecer
                crawler=crawler,
                products_json=None,
                repository=Mock(),
                supabase=None,
                captured_at="2026-10-15T00:00:00-03:00",
                summary=summary,
            )
        )
        return summary

    def test_failure_is_retried_only_for_failed_products(self):
        known = [_record("1"), _record("2"), _record("3")]
        failed_job = ProductJob("2", "https://example.com/catalog/2", "Cozinha")
        crawler = FakeCrawler([[(failed_job, RuntimeError("pagina nao carregou"))], []])
        summary = self._run(crawler, known)
        self.assertIn("Cozinha", summary.balance_only_categories)
        self.assertEqual(summary.full_categories, [])
        self.assertEqual(len(crawler.calls), 2)
        self.assertEqual(crawler.calls[1], [failed_job])

    def test_persistent_failure_marks_category_incomplete_without_full_read(self):
        known = [_record("1"), _record("2")]
        first = [(ProductJob("1", "https://x/catalog/1", "Cozinha"), RuntimeError("falhou"))]
        second = [(ProductJob("1", "https://x/catalog/1", "Cozinha"), RuntimeError("falhou de novo"))]
        crawler = FakeCrawler([first, second])
        summary = self._run(crawler, known)
        self.assertEqual(summary.balance_only_categories, [])
        self.assertEqual(summary.full_categories, [])
        self.assertEqual(len(summary.failed_ids), 1)


if __name__ == "__main__":
    unittest.main()
