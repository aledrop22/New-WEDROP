"""data.json: nunca perde registros, retoma sem repetir e mantém o formato antigo."""

import gzip
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from wedrop.storage import products_file
from wedrop.storage.run_state import COMPLETED, IN_PROGRESS, load_run_state, save_run_state


def _line(product_id: str, price: str = "R$ 1,00") -> dict:
    return {"product_id": product_id, "name": f"Produto {product_id}", "price": price}


class DataFileTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.products = self.folder / "data.json"
        self.backups = self.folder / "backups"

    def test_restore_adds_only_missing_products_and_keeps_existing_ones(self):
        self.products.write_text(json.dumps(_line("1", "R$ 9,99")) + "\n", encoding="utf-8")
        backup = self.backups / "data_backup_20260101_000000.json"
        backup.parent.mkdir()
        backup.write_text(
            "\n".join(json.dumps(_line(str(i), "OLD")) for i in range(1, 4)) + "\n", encoding="utf-8"
        )

        restored = products_file.restore_missing_from_backups(self.products, self.backups)

        self.assertEqual(restored, 2)
        records = {r["product_id"]: r for r in products_file.read_records(self.products)}
        self.assertEqual(records["1"]["price"], "R$ 9,99", "registro existente não pode mudar")
        self.assertEqual(records["3"]["price"], "OLD")

    def test_restore_is_idempotent(self):
        self.products.write_text(json.dumps(_line("1")) + "\n", encoding="utf-8")
        backup = self.backups / "data_backup_20260101_000000.json"
        backup.parent.mkdir()
        backup.write_text(json.dumps(_line("2")) + "\n", encoding="utf-8")
        products_file.restore_missing_from_backups(self.products, self.backups)
        self.assertEqual(products_file.restore_missing_from_backups(self.products, self.backups), 0)

    def test_append_repairs_a_line_left_half_written_by_an_interruption(self):
        self.products.write_text('{"product_id": "1", "na', encoding="utf-8")
        products_file.append_records(self.products, [_line("2")])
        lines = self.products.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], '{"product_id": "1", "na')
        self.assertEqual(json.loads(lines[1])["product_id"], "2")

    def test_invalid_lines_are_kept_verbatim(self):
        self.products.write_text(json.dumps(_line("1")) + "\nlinha quebrada{\n", encoding="utf-8")
        records = products_file.read_records(self.products)
        products_file.write_records_atomic(self.products, records)
        self.assertEqual(self.products.read_text(encoding="utf-8").splitlines()[1], "linha quebrada{")

    def test_old_backups_are_compressed_and_recent_ones_are_kept(self):
        self.backups.mkdir()
        for index in range(4):
            path = self.backups / f"data_backup_2026010{index}_000000.json"
            path.write_text(json.dumps(_line(str(index))) * 50, encoding="utf-8")
            os.utime(path, (time.time() - (10 - index), time.time() - (10 - index)))

        compressed = products_file.compress_old_backups(self.backups, keep=2)

        self.assertEqual(compressed, 2)
        self.assertEqual(len(list(self.backups.glob("*.json"))), 2)
        with gzip.open(self.backups / "data_backup_20260100_000000.json.gz", "rt", encoding="utf-8") as handle:
            self.assertIn('"product_id": "0"', handle.read())

    def test_file_record_keeps_legacy_field_names_used_by_older_scripts(self):
        record = products_file.file_record(
            {"product_id": "7", "name": "Panela", "number_sales": "3", "height": "10"},
            "2026-10-12T10:00:00-03:00",
        )
        self.assertEqual(record["title"], "Panela")
        self.assertEqual(record["numero_vendas"], "3")
        self.assertEqual(record["altura"], "10")
        self.assertEqual(record["scrape_time"], "2026-10-12T10:00:00-03:00")


class RunStateTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.state_file = self.folder / "estado_coleta.json"

    def test_missing_state_means_no_previous_run(self):
        self.assertIsNone(load_run_state(self.state_file))

    def test_saved_state_round_trips(self):
        save_run_state(self.state_file, IN_PROGRESS, site_total=1276, saved_total=10)
        state = load_run_state(self.state_file)
        self.assertTrue(state.is_in_progress)
        self.assertEqual((state.site_total, state.saved_total), (1276, 10))

    def test_unreadable_state_is_treated_as_interrupted_so_it_resumes(self):
        self.state_file.write_text("{ não é json", encoding="utf-8")
        self.assertTrue(load_run_state(self.state_file).is_in_progress)

    def test_completed_state_is_not_in_progress(self):
        save_run_state(self.state_file, COMPLETED)
        self.assertFalse(load_run_state(self.state_file).is_in_progress)


if __name__ == "__main__":
    unittest.main()
