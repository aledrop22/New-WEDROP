"""Funções puras que interpretam textos das páginas do WeDrop (sem navegador)."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any
from urllib.parse import urlparse

_PRODUCT_PATH = re.compile(
    r"/catalog/(?:[^/?#]+/)*(?:"
    r"(\d+)|([0-9a-f]{8}-[0-9a-f-]{27,})"
    r")(?:/[^/?#]+)?/?$",
    re.IGNORECASE,
)
_MONEY = re.compile(r"R\$\s*[\d.,]+")
_MONEY_LAST_RESORT = re.compile(r"R\$\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?")
_MOVEMENT_ENTRY = "ENTRADA"
_MOVEMENT_EXIT = frozenset({"SAÍDA", "SAIDA"})
_STOCK_PLACEHOLDERS = frozenset({"DISPONÍVEL", "INDISPONÍVEL"})

# Rótulo da página -> campo do produto.
SPEC_LABEL_FIELDS = {
    "ncm": "ncm",
    "peso": "weight",
    "altura": "height",
    "largura": "width",
    "comprimento": "length",
    "descrição": "description",
}


def product_id_from_url(url: str) -> str:
    """ID do produto a partir do endereço /catalog/<id>/<slug>."""
    match = _PRODUCT_PATH.search(urlparse(url).path)
    if not match:
        return ""
    return next((group for group in match.groups() if group), "")


def value_for_label(text: str, labels: Sequence[str]) -> str:
    """Valor de uma linha do tipo 'Rótulo: valor'."""
    alternatives = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"^\s*(?:{alternatives})\s*:?\s*(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def first_non_empty(values: Iterable[str | None]) -> str:
    return next((value for value in values if value), "")


def first_non_generic(values: Iterable[str | None], generic: frozenset[str]) -> str:
    return next(
        (value for value in values if value and value.casefold() not in generic), ""
    )


def has_money_value(text: str) -> bool:
    return bool(_MONEY.search(text))


def last_resort_price(page_text: str) -> str:
    """Primeiro valor em R$ do texto da página; usado só quando nenhum seletor achou o preço."""
    matches = _MONEY_LAST_RESORT.findall(page_text)
    return matches[0].strip() if matches else ""


def sku_from_text(text: str) -> str:
    match = re.search(r"SKU:\s*([^|]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def ean_from_text(text: str) -> str:
    match = re.search(r"EAN:\s*([^|]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_sales_count(value: str) -> str:
    """Número de vendas como texto puro; rejeita valores que não sejam só dígitos."""
    match = re.fullmatch(r"\s*(\d[\d.,]*)\s*", value)
    return str(int(re.sub(r"\D", "", match.group(1)))) if match else ""


def parse_first_int(text: str) -> int | None:
    match = re.search(r"\d[\d.,]*", text)
    if not match:
        return None
    return int(re.sub(r"\D", "", match.group()))


def _first_number(text: str) -> int | None:
    match = re.search(r"\d+", text)
    return int(match.group()) if match else None


def _initial_balance(history: list[dict[str, Any]]) -> int:
    """Saldo inicial: primeiro registro sem tipo de movimento e com quantidade positiva sem sinal."""
    for movement in history:
        kind = str(movement.get("type", "")).upper()
        if kind == _MOVEMENT_ENTRY or kind in _MOVEMENT_EXIT:
            continue
        quantity = str(movement.get("quantity", ""))
        number = _first_number(quantity)
        if number and number > 0 and "+" not in quantity and "-" not in quantity:
            return number
    return 0


def calculate_current_balance(history: list[dict[str, Any]]) -> int:
    """Saldo atual: saldo inicial + entradas - saídas do histórico de movimentações."""
    if not history:
        return 0
    balance = _initial_balance(history)
    for movement in history:
        kind = str(movement.get("type", "")).upper()
        number = _first_number(str(movement.get("quantity", "")))
        if number is None:
            continue
        if kind == _MOVEMENT_ENTRY:
            balance += number
        elif kind in _MOVEMENT_EXIT:
            balance -= number
    return balance


def stock_from_candidates(candidates: Iterable[str | None]) -> str:
    """Primeiro texto com dígitos que não seja apenas DISPONÍVEL/INDISPONÍVEL."""
    for text in candidates:
        if text and re.search(r"\d+", text) and text not in _STOCK_PLACEHOLDERS:
            return text
    return ""
