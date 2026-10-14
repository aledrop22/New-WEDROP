"""Pente fino nos dados do catálogo WeDrop.

Corrige nomes vazios, prefixos "WE DROP" e títulos genéricos tanto no
``data.json`` quanto no banco SQLite (``wedrop_monitoramento.db``) usado pelo
painel. A descrição do produto é usada como fallback para recuperar o nome.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
from pathlib import Path

from product_naming import clean_product_name

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data.json"
BACKUP_FILE = BASE_DIR / "data_backup.json"
DB_FILE = BASE_DIR / "wedrop_monitoramento.db"
DB_BACKUP_FILE = BASE_DIR / "wedrop_monitoramento.db.bak"


def correct_name(original_name: str, description: str) -> str:
    return clean_product_name(original_name or "", description or "")


def correct_product_data(product: dict) -> tuple[dict, bool]:
    corrected = dict(product)
    original_name = corrected.get("name", "") or ""
    description = corrected.get("description", "") or ""
    corrected_name = correct_name(original_name, description)
    changed = False

    if corrected_name != original_name:
        corrected["name"] = corrected_name
        corrected["title"] = corrected_name
        changed = True

    price = corrected.get("price", "") or ""
    if not str(price).strip():
        price_match = re.search(r"R\$\s*[\d.,]+", description)
        if price_match:
            corrected["price"] = price_match.group()
            changed = True

    return corrected, changed


def correct_data_json() -> None:
    print("\n== data.json ==")
    if DATA_FILE.exists():
        shutil.copy(DATA_FILE, BACKUP_FILE)
        print(f"Backup criado: {BACKUP_FILE.name}")

    corrected_count = 0
    total_count = 0
    still_empty = 0
    products = []

    with DATA_FILE.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            try:
                product = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  Erro ao decodificar linha: {exc}")
                continue
            total_count += 1
            corrected_product, changed = correct_product_data(product)
            products.append(corrected_product)
            if changed:
                corrected_count += 1
            if not (corrected_product.get("name") or "").strip():
                still_empty += 1

    with DATA_FILE.open("w", encoding="utf-8", newline="\n") as outfile:
        for product in products:
            outfile.write(json.dumps(product, ensure_ascii=False) + "\n")

    print(f"  Total de produtos: {total_count}")
    print(f"  Produtos corrigidos: {corrected_count}")
    print(f"  Nomes ainda vazios: {still_empty}")


def correct_database() -> None:
    print("\n== wedrop_monitoramento.db ==")
    if not DB_FILE.exists():
        print("  Banco não encontrado, pulando.")
        return

    shutil.copy(DB_FILE, DB_BACKUP_FILE)
    print(f"Backup criado: {DB_BACKUP_FILE.name}")

    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT product_id, name, description FROM products"
        ).fetchall()

        updates = []
        for row in rows:
            original = row["name"] or ""
            corrected = correct_name(original, row["description"] or "")
            if corrected != original:
                updates.append((corrected, row["product_id"]))

        connection.executemany(
            "UPDATE products SET name = ? WHERE product_id = ?", updates
        )
        connection.commit()

        total = len(rows)
        still_empty = connection.execute(
            "SELECT COUNT(*) FROM products WHERE TRIM(COALESCE(name, '')) = ''"
        ).fetchone()[0]
        remaining_we = connection.execute(
            "SELECT COUNT(*) FROM products "
            "WHERE UPPER(TRIM(COALESCE(name, ''))) LIKE 'WE DROP%' "
            "OR UPPER(TRIM(COALESCE(name, ''))) LIKE 'WEDROP%'"
        ).fetchone()[0]
    finally:
        connection.close()

    print(f"  Total de produtos: {total}")
    print(f"  Produtos corrigidos: {len(updates)}")
    print(f"  Nomes ainda vazios: {still_empty}")
    print(f"  Nomes ainda com WE DROP: {remaining_we}")


def main() -> None:
    print("Iniciando pente fino no catálogo WeDrop...")
    correct_data_json()
    correct_database()
    print("\nPente fino concluído.")


if __name__ == "__main__":
    main()
