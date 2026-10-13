"""Normalize WeDrop product names from page titles and descriptions."""

from __future__ import annotations

import re

WE_DROP_PREFIX = re.compile(
    r"^(?:produto\s*[-–:]\s*)?(?:we\s*drop|wedrop|we-drop)\s*[-–:]?\s*",
    re.IGNORECASE,
)
WE_DROP_SUFFIX = re.compile(
    r"\s*[-–]\s*(?:resumo geral\s*[-–]\s*)?(?:we\s*drop|wedrop|we-drop)\s*$",
    re.IGNORECASE,
)
GENERIC_NAMES = {
    "",
    "produto",
    "product",
    "produto - wedrop",
    "produto wedrop",
    "wedrop",
    "we drop",
    "resumo geral",
    "resumo geral - wedrop",
    "resumo geral wedrop",
}
MARKETING_STARTERS = (
    "ideal para",
    "chegou a",
    "chegou o",
    "chegou as",
    "chegou os",
    "uma solu",
    "com seus",
    "com suas",
    "a fase de",
    "para organizar",
    "para quem",
    "tenha sempre",
    "viaje com",
    "projetado para",
    "projetada para",
    "feito para",
    "feita para",
    "muito além",
    "esse protetor",
    "para furadeira",
    "a escolha",
    "desenvolvido para",
    "desenvolvida para",
    "mais conserv",
    "praticidade",
    "o conjunto conta",
    "conjunto conta",
    "transforme",
    "este escorredor",
    "essa ",
    "esse ",
    "esta ",
    "esta ",
    "com design",
)
CONTEM_RE = re.compile(
    r"cont[eé]m\s*[:;]?\s*(?:0?1\s*)?(.+)",
    re.IGNORECASE,
)
PRODUTO_LABEL_RE = re.compile(
    r"(?:produto|nome do produto|modelo)\s*[:-]\s*(.+)",
    re.IGNORECASE,
)
LEADING_CODE_RE = re.compile(r"^(?:0?1\s*[^\w\s]*\s*|\d{1,3}\s*[\-–x×]\s*)")
TITLE_SPLIT_RE = re.compile(r"(?:\s{2,}|\u00a0+|[\r\n]+)")


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip(" -–:\t")


def strip_we_drop_prefix(text: str) -> str:
    """Remove WE DROP / WeDrop / Produto - WeDrop from the start and end."""
    cleaned = _normalize_spaces(text)
    while True:
        updated = _normalize_spaces(WE_DROP_PREFIX.sub("", cleaned, count=1))
        updated = _normalize_spaces(WE_DROP_SUFFIX.sub("", updated))
        if updated == cleaned:
            return cleaned
        cleaned = updated


def _short_title(text: str) -> str:
    prepared = (text or "").replace("\xa0", "  ")
    split = re.split(r"(?:\s{2,}|[\r\n]+)", prepared, maxsplit=1)
    title = _normalize_spaces(split[0]) if split else prepared
    return title[:150]


def _is_generic(name: str) -> bool:
    return strip_we_drop_prefix(name).casefold() in GENERIC_NAMES


def _looks_like_marketing(text: str) -> bool:
    if not text:
        return True
    lowered = text.casefold()
    if any(lowered.startswith(prefix) for prefix in MARKETING_STARTERS):
        return True
    if text.count(",") >= 3 or text.count("!") >= 1 and len(text) > 60:
        return True
    if len(text) > 120:
        return True
    return False


def _is_good_name(name: str) -> bool:
    n = _normalize_spaces(name)
    if not n or _is_generic(n):
        return False
    if _looks_like_marketing(n):
        return False
    return True


def _clean_candidate(text: str) -> str:
    candidate = strip_we_drop_prefix(
        re.split(r"[\r\n]+", text or "", maxsplit=1)[0]
    )
    candidate = LEADING_CODE_RE.sub("", candidate)
    candidate = re.sub(r"^[.\-–•*]+\s*", "", candidate)
    return _normalize_spaces(candidate)[:150]


def _name_from_contem(description: str) -> str:
    for regex in (CONTEM_RE, PRODUTO_LABEL_RE):
        match = regex.search(description or "")
        if not match:
            continue
        candidate = _clean_candidate(match.group(1))
        if _is_good_name(candidate) and len(candidate) >= 8:
            return candidate
    return ""


def _name_from_first_line(description: str) -> str:
    lines = [
        line.strip()
        for line in re.split(r"[\r\n]+", description or "")
        if line.strip()
    ]
    if not lines:
        return ""
    title = _clean_candidate(_short_title(lines[0]))
    if len(title) < 8 or not _is_good_name(title):
        return ""
    return title


def extract_name_from_description(description: str) -> str:
    first_line = _name_from_first_line(description)
    if first_line:
        return first_line
    return _name_from_contem(description)


def clean_product_name(name: str, description: str = "") -> str:
    """Return a proper product name, stripping the WE DROP prefix.

    The page name is kept when it already looks like a real product name;
    otherwise the name is recovered from the description (first line or the
    ``Contém:`` section). A reasonable name is never blanked out.
    """
    current = _short_title(strip_we_drop_prefix(name))
    description = description or ""

    if _is_good_name(current):
        return current

    extracted = extract_name_from_description(description)
    if extracted and not _is_generic(extracted):
        return extracted

    # Se ainda não tem nome bom, usa o que tiver mesmo que não seja perfeito
    if current and len(current) >= 3:
        return current

    # Último recurso: retorna o nome original mesmo que genérico
    original_cleaned = strip_we_drop_prefix(name)
    if original_cleaned and len(original_cleaned) >= 3:
        return original_cleaned

    return ""
