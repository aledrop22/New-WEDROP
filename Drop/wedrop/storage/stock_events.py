"""Interpretação das movimentações de estoque (funções puras, sem I/O)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from typing import Any

SALE_KIND = "sale"
STOCK_IN_KIND = "stock_in"
OTHER_KIND = "other"


def parse_event_datetime(value: str) -> datetime | None:
    """Lê as datas no formato que aparece no histórico de estoque do WeDrop."""
    text = value.strip().replace("\u00a0", " ")
    text = re.sub(r"\s*,\s*", " ", text)  # o site grava "12/10/2026, 19:01:05"
    text = re.sub(r"\s+às\s+", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<=\d)h(?=\d)", ":", text, flags=re.IGNORECASE)
    for pattern in (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
    ):
        try:
            parsed = datetime.strptime(text, pattern)
        except ValueError:
            continue
        return parsed.astimezone()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.astimezone()


def parse_quantity(value: str) -> int:
    """Quantidade absoluta de um texto como '- 2 un.'."""
    digits = re.sub(r"\D", "", value)
    return int(digits) if digits else 0


def classify_movement(value: str) -> str:
    """Classifica o tipo da movimentação em venda, entrada de estoque ou outra."""
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    if "venda" in normalized or "saida" in normalized:
        return SALE_KIND
    if "entrada" in normalized or "recebimento" in normalized:
        return STOCK_IN_KIND
    return OTHER_KIND


def event_fingerprint(product_id: str, event: dict[str, Any]) -> str:
    """Identificador estável de uma movimentação; evita duplicar ao reler o catálogo."""
    fields = (
        product_id,
        str(event.get("type", "")).strip().casefold(),
        str(event.get("quantity", "")).strip(),
        str(event.get("date", "")).strip(),
        str(event.get("nf_key", "")).strip(),
    )
    return hashlib.sha256("\x1f".join(fields).encode("utf-8")).hexdigest()


def make_event_records(product: dict[str, Any], captured_at: str) -> list[dict[str, Any]]:
    """Transforma o histórico de um produto em registros prontos para o banco."""
    records = []
    for event in product.get("stock_history", []):
        raw_date = str(event.get("date", "")).strip()
        parsed_date = parse_event_datetime(raw_date)
        movement_type = str(event.get("type", "")).strip()
        records.append(
            {
                "event_id": event_fingerprint(product["product_id"], event),
                "product_id": product["product_id"],
                "movement_type": movement_type,
                "event_kind": classify_movement(movement_type),
                "quantity": parse_quantity(str(event.get("quantity", ""))),
                "event_at": parsed_date.isoformat(timespec="seconds") if parsed_date else None,
                "event_at_raw": raw_date,
                "nf_key": str(event.get("nf_key", "")).strip(),
                "recorded_at": captured_at,
            }
        )
    return records
