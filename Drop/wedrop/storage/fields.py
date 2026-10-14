"""Campos de produto gravados no SQLite e no Supabase."""

from __future__ import annotations

UPDATED_AT = "updated_at"
# Quando o preço mudou em relação à coleta anterior (o preço antigo não é guardado).
PRICE_ALERT_FIELD = "price_changed_at"
# Campos de data que aceitam vazio: vazio vira NULL no Supabase.
NULLABLE_TIMESTAMP_FIELDS: tuple[str, ...] = (PRICE_ALERT_FIELD,)

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
    PRICE_ALERT_FIELD,
)

PRODUCT_FIELDS: tuple[str, ...] = (*PRODUCT_DATA_FIELDS, UPDATED_AT)
