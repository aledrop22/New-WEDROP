"""Rastreia produtos que falharam ao serem lidos em cada categoria.

Quando uma categoria não completa, salvamos quais produtos específicos
não foram lidos. Na próxima execução, lemos apenas esses produtos,
em vez de reler toda a categoria.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FailedProduct:
    """Produto que falhou ao ser lido."""
    product_id: str
    url: str
    category_name: str
    error: str = ""
    failed_at: str = ""


@dataclass(frozen=True)
class CategoryFailures:
    """Produtos que falharam em uma categoria específica."""
    category_name: str
    products: list[FailedProduct]
    site_total: int = 0
    saved_total: int = 0
    updated_at: str = ""


def load_category_failures(path: Path) -> dict[str, CategoryFailures]:
    """Carrega os produtos que falharam por categoria."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    
    failures = {}
    for category_name, category_data in data.items():
        products = [
            FailedProduct(
                product_id=p["product_id"],
                url=p["url"],
                category_name=p["category_name"],
                error=p.get("error", ""),
                failed_at=p.get("failed_at", ""),
            )
            for p in category_data.get("products", [])
        ]
        failures[category_name] = CategoryFailures(
            category_name=category_name,
            products=products,
            site_total=category_data.get("site_total", 0),
            saved_total=category_data.get("saved_total", 0),
            updated_at=category_data.get("updated_at", ""),
        )
    return failures


def save_category_failures(path: Path, failures: dict[str, CategoryFailures]) -> None:
    """Salva os produtos que falharam por categoria."""
    data = {
        category_name: {
            "products": [asdict(p) for p in cat_failures.products],
            "site_total": cat_failures.site_total,
            "saved_total": cat_failures.saved_total,
            "updated_at": cat_failures.updated_at,
        }
        for category_name, cat_failures in failures.items()
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def add_failed_products(
    path: Path,
    category_name: str,
    failed_products: list[tuple[str, str, str]],  # (product_id, url, error)
    site_total: int = 0,
    saved_total: int = 0,
) -> None:
    """Adiciona produtos que falharam a uma categoria."""
    failures = load_category_failures(path)
    
    # Remove produtos que já foram salvos com sucesso (não devem estar na lista)
    existing = failures.get(category_name)
    existing_ids = {p.product_id for p in existing.products} if existing else set()
    
    # Adiciona novos produtos que falharam
    new_products = [
        FailedProduct(
            product_id=product_id,
            url=url,
            category_name=category_name,
            error=error,
            failed_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        for product_id, url, error in failed_products
        if product_id not in existing_ids
    ]
    
    if new_products or existing:
        all_products = (existing.products if existing else []) + new_products
        failures[category_name] = CategoryFailures(
            category_name=category_name,
            products=all_products,
            site_total=site_total,
            saved_total=saved_total,
            updated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        save_category_failures(path, failures)


def clear_category_failures(path: Path, category_name: str) -> None:
    """Remove uma categoria da lista de falhas (quando completar)."""
    failures = load_category_failures(path)
    if category_name in failures:
        del failures[category_name]
        save_category_failures(path, failures)


def get_failed_products_for_category(path: Path, category_name: str) -> list[FailedProduct]:
    """Retorna os produtos que falharam em uma categoria específica."""
    failures = load_category_failures(path)
    category_failures = failures.get(category_name)
    return category_failures.products if category_failures else []
