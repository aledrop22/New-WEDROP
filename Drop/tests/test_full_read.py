"""Quando a categoria inteira precisa ser lida (e quando basta preço e saldo)."""

from __future__ import annotations

import unittest

from wedrop.mapping import _full_read_reason
from wedrop.scraping.catalog import Category


def _category(count: int | None) -> Category:
    return Category(name="Cozinha", url="https://example.com/cozinha", count=count)


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


if __name__ == "__main__":
    unittest.main()
