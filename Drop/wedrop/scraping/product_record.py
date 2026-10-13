"""Monta o registro de um produto a partir dos textos capturados na página.

Esta função não acessa o navegador: recebe os textos já lidos e aplica as
regras de negócio (nome, preço, saldo, situação). Por isso é testável.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ..names import clean_product_name
from .parsing import (
    SPEC_LABEL_FIELDS,
    calculate_current_balance,
    ean_from_text,
    first_non_empty,
    first_non_generic,
    has_money_value,
    last_resort_price,
    parse_sales_count,
    sku_from_text,
    stock_from_candidates,
    value_for_label,
)

GENERIC_NAMES = frozenset({"produto", "product", "wedrop"})
_NO_HISTORY = {"type": "NÃO HOUVE MOVIMENTAÇÃO DE SALDO", "quantity": "", "date": "", "nf_key": ""}
_TITLE_PREFIX = re.compile(r"^(?:we\s*drop|wedrop|we-drop)\s*[-–:]?\s*", re.IGNORECASE)


@dataclass(frozen=True)
class PageSnapshot:
    """Textos capturados da página do produto, na ordem em que a página é lida."""

    title: str = ""
    body_text: str = ""
    name_candidates: tuple[str, ...] = ()
    sku_ean_text: str = ""
    price_candidates: tuple[str, ...] = ()
    alt_price_candidates: tuple[str, ...] = ()
    availability_candidates: tuple[str, ...] = ()
    description: str = ""
    spec_rows: tuple[tuple[str, str], ...] = ()
    stock_candidates: tuple[str, ...] = ()
    history_rows: tuple[dict[str, str], ...] = ()
    body_text_after_stock_tab: str | None = None


def _page_name(snapshot: PageSnapshot) -> str:
    """Primeiro título que não é genérico; se nenhum servir, usa o título da aba."""
    name = first_non_generic(snapshot.name_candidates, GENERIC_NAMES)
    if name:
        return name
    title = _TITLE_PREFIX.sub("", snapshot.title.strip())
    return title if title.casefold() not in GENERIC_NAMES | {"wedrop"} else ""


def _price(snapshot: PageSnapshot, page_text: str) -> str:
    price = first_non_empty(snapshot.price_candidates)
    if price:
        return price
    price = next((text for text in snapshot.alt_price_candidates if text and has_money_value(text)), "")
    return price or last_resort_price(page_text)


def _movements(rows: tuple[dict[str, str], ...]) -> list[dict[str, str]]:
    """Movimentações válidas: precisam de tipo e de quantidade."""
    movements = []
    for row in rows:
        movement_type, quantity = row.get("type", ""), row.get("quantity", "")
        if not (movement_type and quantity):
            continue
        nf_match = re.search(r"Chave da NF:\s*(.+)", row.get("row_text", ""), re.IGNORECASE)
        movements.append(
            {
                "type": movement_type,
                "quantity": quantity,
                "date": row.get("date", ""),
                "nf_key": nf_match.group(1).strip() if nf_match else "",
            }
        )
    return movements


def _label_from_any(texts: list[str], labels: tuple[str, ...]) -> str:
    """Primeiro valor encontrado nos textos da página (texto da aba atual, depois o inicial)."""
    return next((value for value in (value_for_label(text, labels) for text in texts if text) if value), "")


def _status(page_text: str) -> str:
    status = value_for_label(page_text, ("Status", "Situação"))
    if status:
        return status
    if re.search(r"\b(desativado|inativo)\b", page_text, re.IGNORECASE):
        return "Inativo"
    if re.search(r"\b(ativo|ativado)\b", page_text, re.IGNORECASE):
        return "Ativo"
    return ""


def _stock_values(
    snapshot: PageSnapshot, page_text: str, availability: str, calculated: int
) -> tuple[str, str, str]:
    """Estoque, saldo real e estoque total, com o saldo calculado como reserva."""
    stock = stock_from_candidates(snapshot.stock_candidates)
    if not stock:
        stock = value_for_label(
            page_text, ("Estoque", "Disponibilidade", "Saldo disponível", "Estoque disponível")
        ) or availability
    if (not stock or stock in {"DISPONÍVEL", "INDISPONÍVEL"}) and calculated > 0:
        stock = str(calculated)

    if calculated > 0:
        real_balance = value_for_label(page_text, ("Saldo real", "Saldo")) or str(calculated)
        total_stock = value_for_label(page_text, ("Estoque total", "Total em estoque")) or str(calculated)
    else:
        real_balance = total_stock = stock
    return stock, real_balance, total_stock


def build_product_record(
    product_id: str, url: str, category_name: str, snapshot: PageSnapshot
) -> dict[str, Any]:
    """Registro completo de um produto, pronto para data.json, SQLite e Supabase."""
    page_text = snapshot.body_text_after_stock_tab or snapshot.body_text
    # Dados do fornecedor podem estar em outra aba; procura no texto de todas as leituras.
    page_texts = [page_text, snapshot.body_text]
    specs = {
        SPEC_LABEL_FIELDS[label.casefold().rstrip(":")]: value
        for label, value in snapshot.spec_rows
        if label and label.casefold().rstrip(":") in SPEC_LABEL_FIELDS
    }
    description = snapshot.description or specs.get("description", "")
    sku = sku_from_text(snapshot.sku_ean_text or snapshot.body_text)
    ean = ean_from_text(snapshot.sku_ean_text or snapshot.body_text)
    availability = first_non_empty(snapshot.availability_candidates)
    movements = _movements(snapshot.history_rows)
    calculated = calculate_current_balance(movements)
    stock, real_balance, total_stock = _stock_values(snapshot, page_text, availability, calculated)

    name = clean_product_name(_page_name(snapshot), description)
    if len(name) < 3:
        name = f"Produto {sku}" if sku else f"Produto {product_id} ({category_name})"

    return {
        "product_id": product_id,
        "name": name,
        "category": category_name,
        "url": url,
        "sku": sku,
        "ean": ean,
        "price": _price(snapshot, snapshot.body_text) or value_for_label(page_text, ("Preço",)),
        "availability": availability,
        "stock": stock,
        "total_stock_count": total_stock,
        "real_balance": real_balance,
        "is_active": _status(page_text),
        "supplier": _label_from_any(page_texts, ("Fornecedor",)),
        "cnpj": _label_from_any(page_texts, ("CNPJ", "CNPJ do fornecedor")),
        "origin_state": _label_from_any(page_texts, ("Estado de origem", "Origem")),
        "ncm": specs.get("ncm", ""),
        "weight": specs.get("weight", ""),
        "height": specs.get("height", ""),
        "width": specs.get("width", ""),
        "length": specs.get("length", ""),
        "description": description,
        "number_sales": parse_sales_count(value_for_label(page_text, ("Vendas", "Número de vendas"))),
        "stock_history": movements or [dict(_NO_HISTORY)],
    }
