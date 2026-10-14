"""Script para analisar produtos com nomes vazios"""

import json
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data_backup.json"

def analyze_empty_names():
    """Analisa produtos com nomes vazios"""
    empty_name_products = []

    with DATA_FILE.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                product = json.loads(line)
                name = product.get("name", "")
                title = product.get("title", "")
                description = product.get("description", "")

                if not name or len(name) < 3:
                    empty_name_products.append({
                        "line": line_num,
                        "product_id": product.get("product_id"),
                        "name": name,
                        "title": title,
                        "description": description[:200] if description else "",
                        "category": product.get("category", ""),
                    })

                    if len(empty_name_products) >= 10:
                        break
            except json.JSONDecodeError:
                continue

    print(f"Encontrados {len(empty_name_products)} produtos com nome vazio (mostrando os primeiros 10):\n")

    for i, p in enumerate(empty_name_products, 1):
        print(f"{'='*80}")
        print(f"Produto {i} (Linha {p['line']}, ID: {p['product_id']})")
        print(f"Categoria: {p['category']}")
        print(f"Name: '{p['name']}'")
        print(f"Title: '{p['title']}'")
        print(f"Description: '{p['description']}'")
        print()

if __name__ == "__main__":
    analyze_empty_names()
