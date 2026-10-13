"""Situação do produto (ativo/inativo) a partir do que o site mostra.

O site não tem um texto "Ativo" ou "Inativo" na página do produto. O que existe é
o selo de disponibilidade: "Disponível" (produto ativo) e "Indisponível" (inativo).
"""

from __future__ import annotations

import unicodedata

ACTIVE = "Ativo"
INACTIVE = "Inativo"


def _plain(text: str | None) -> str:
    """Minúsculo e sem acentos, para comparar 'Disponível' com 'DISPONÍVEL'."""
    normalized = unicodedata.normalize("NFKD", (text or "").strip().casefold())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def status_from_availability(availability: str | None) -> str:
    plain = _plain(availability)
    if plain == "disponivel":
        return ACTIVE
    if plain == "indisponivel":
        return INACTIVE
    return ""


def effective_status(is_active: str | None, availability: str | None) -> str:
    """Situação gravada na página; se ela não existir, a derivada da disponibilidade."""
    return (is_active or "").strip() or status_from_availability(availability)
