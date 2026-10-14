"""Alerta de alteração de preço: só a data da mudança é guardada (o preço antigo não)."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from wedrop.scraping.product_record import fill_from_known, with_price_alert
from wedrop.storage.fields import PRICE_ALERT_FIELD, PRODUCT_DATA_FIELDS
from wedrop.storage.supabase_repository import SupabaseRepository, _column_value

NOW = "2026-10-14T00:03:00-03:00"
EARLIER = "2026-10-13T00:04:00-03:00"


def _known(**overrides):
    record = {"product_id": "1", "price": "R$ 10,00", "stock": "5", "name": "Produto", "price_changed_at": ""}
    return {**record, **overrides}


class PriceAlertRuleTest(unittest.TestCase):
    def test_marks_date_when_price_differs(self):
        record = with_price_alert({**_known(), "price": "R$ 12,00"}, _known(), NOW)
        self.assertEqual(record[PRICE_ALERT_FIELD], NOW)
        self.assertEqual(record["price"], "R$ 12,00")

    def test_same_price_keeps_no_alert(self):
        record = with_price_alert(_known(), _known(), NOW)
        self.assertEqual(record[PRICE_ALERT_FIELD], "")

    def test_first_price_is_not_a_change(self):
        known = _known(price="")
        record = with_price_alert({**_known(), "price": "R$ 12,00"}, known, NOW)
        self.assertEqual(record[PRICE_ALERT_FIELD], "")

    def test_new_product_has_no_alert(self):
        record = with_price_alert({"product_id": "2", "price": "R$ 9,00"}, None, NOW)
        self.assertNotIn(PRICE_ALERT_FIELD, record)

    def test_full_reread_keeps_previous_alert_date(self):
        known = _known(price_changed_at=EARLIER)
        reread = {"product_id": "1", "price": "R$ 10,00", "stock": "7", "name": "Produto"}
        filled = fill_from_known(reread, known)
        self.assertEqual(filled[PRICE_ALERT_FIELD], EARLIER)

    def test_full_reread_with_new_price_moves_alert_to_now(self):
        known = _known(price_changed_at=EARLIER)
        reread = {"product_id": "1", "price": "R$ 12,00", "stock": "7", "name": "Produto"}
        record = with_price_alert(fill_from_known(reread, known), known, NOW)
        self.assertEqual(record[PRICE_ALERT_FIELD], NOW)


class SupabaseRowTest(unittest.TestCase):
    def test_empty_alert_date_is_sent_as_null(self):
        self.assertIsNone(_column_value({PRICE_ALERT_FIELD: ""}, PRICE_ALERT_FIELD))
        self.assertIsNone(_column_value({}, PRICE_ALERT_FIELD))

    def test_other_empty_fields_keep_empty_text(self):
        self.assertEqual(_column_value({}, "sku"), "")
        self.assertIn(PRICE_ALERT_FIELD, PRODUCT_DATA_FIELDS)

    def test_validate_reports_missing_alert_column(self):
        repository = SupabaseRepository("https://example.supabase.co", "test-key")
        ok = Mock(spec=requests.Response)
        ok.ok = True
        missing_column = Mock(spec=requests.Response)
        missing_column.ok = False
        missing_column.status_code = 400
        missing_column.text = "column does not exist"
        with patch.object(repository.session, "get", side_effect=[ok, ok, ok, missing_column]):
            with self.assertRaisesRegex(RuntimeError, PRICE_ALERT_FIELD):
                repository.validate()
        repository.close()


if __name__ == "__main__":
    unittest.main()
