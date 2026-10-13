"""Campos de produto gravados no SQLite e no Supabase."""

from __future__ import annotations

UPDATED_AT = "updated_at"

# Campos do produto, sem o carimbo de data da gravação.
PRODUCT_DATA_FIELDS: tuple[str, ...] = (
    "product_id",
    "name",
    "category",
    "url",
    "sku",
    "ean",
    "price",
    "availability",
    "stock",
    "total_stock_count",
    "real_balance",
    "is_active",
    "supplier",
    "cnpj",
    "origin_state",
    "ncm",
    "weight",
    "height",
    "width",
    "length",
    "description",
    "number_sales",
)

PRODUCT_FIELDS: tuple[str, ...] = (*PRODUCT_DATA_FIELDS, UPDATED_AT)
