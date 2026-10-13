"""Situação do produto: 'Disponível' é ativo, 'Indisponível' é inativo."""

import unittest
from datetime import date

from wedrop.scraping.product_record import PageSnapshot, build_product_record
from wedrop.storage.product_status import effective_status, status_from_availability
from wedrop.storage.sqlite_repository import SalesRepository


class ProductStatusTests(unittest.TestCase):
    def test_availability_badge_maps_to_active_or_inactive(self):
        self.assertEqual(status_from_availability("Disponível"), "Ativo")
        self.assertEqual(status_from_availability("DISPONÍVEL"), "Ativo")
        self.assertEqual(status_from_availability("Indisponível"), "Inativo")
        self.assertEqual(status_from_availability("INDISPONÍVEL"), "Inativo")
        self.assertEqual(status_from_availability(""), "")
        self.assertEqual(status_from_availability(None), "")

    def test_status_read_from_page_wins_over_availability(self):
        self.assertEqual(effective_status("Inativo", "DISPONÍVEL"), "Inativo")
        self.assertEqual(effective_status("", "INDISPONÍVEL"), "Inativo")

    def test_product_record_takes_status_from_availability_badge(self):
        snapshot = PageSnapshot(name_candidates=("Caixa Organizadora",), availability_candidates=("Indisponível",))
        record = build_product_record("1", "https://x/1", "Cozinha", snapshot)
        self.assertEqual(record["is_active"], "Inativo")

    def test_dashboard_counts_active_and_inactive_products(self):
        snapshot = {
            "categories": [
                {"category_url": "https://x/cozinha", "name": "Cozinha", "expected_products": 2,
                 "mapped_products": 2, "updated_at": "2026-10-12T10:00:00+00:00"},
            ],
            "products": [
                {"product_id": "1", "name": "Panela", "category": "Cozinha", "url": "https://x/1",
                 "availability": "DISPONÍVEL", "is_active": "", "updated_at": "2026-10-12T10:00:00+00:00"},
                {"product_id": "2", "name": "Faca", "category": "Cozinha", "url": "https://x/2",
                 "availability": "INDISPONÍVEL", "is_active": "", "updated_at": "2026-10-12T10:00:00+00:00"},
            ],
            "stock_events": [],
        }
        repository = SalesRepository.from_snapshot(snapshot)
        self.addCleanup(repository.close)
        (row,) = repository.category_activity(date(2026, 10, 1), date(2026, 10, 12))
        self.assertEqual(row["active_products"], 1)
        self.assertEqual(row["inactive_products"], 1)
        self.assertEqual(row["products_without_status"], 0)
        statuses = {p["product_id"]: p["is_active"] for p in repository.products_for_category_period("Cozinha", date(2026, 10, 1), date(2026, 10, 12))}
        self.assertEqual(statuses, {"1": "Ativo", "2": "Inativo"})


if __name__ == "__main__":
    unittest.main()
