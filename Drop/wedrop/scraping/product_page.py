"""Leitura de uma página de produto do WeDrop.

Cada página é lida com poucas chamadas ao navegador: um snapshot do DOM
(textos de nome, preço, SKU etc.) e, depois de trocar de aba, outro snapshot
do histórico. Antes eram dezenas de consultas separadas por produto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..logs import log_progress
from ..config import PRODUCT_READ_ATTEMPTS
from .product_record import PageSnapshot, build_product_record
from .session import SessionExpiredError

READY_SELECTOR = (
    "h2.chakra-heading, p.chakra-text.css-1enygfq, p[class*='1enygfq'], p[class*='1hulv5q']"
)
STOCK_TAB_NAME = re.compile("(Valores|Estoque|Saldo)", re.IGNORECASE)
HISTORY_TAB_NAME = re.compile("Histórico de Estoque", re.IGNORECASE)
TAB_CONTENT_TIMEOUT_MS = 3000
_LOAD_TIMEOUT_MS = 12_000
_CNPJ_RETRY_WAIT_MS = 1500
_PRODUCT_LOADED_JS = """() => {
  const filled = (selector) => {
    const element = document.querySelector(selector);
    return !!element && element.innerText.trim().length > 0;
  };
  return filled("h2.chakra-heading.css-18puvtl, h2.chakra-heading, h1.chakra-heading")
    || filled("p.chakra-text.css-1enygfq")
    || filled("p[class*='1hulv5q']");
}"""

_NAME_SELECTORS = (
    "h2.chakra-heading.css-18puvtl",
    "h1.chakra-heading",
    "h2.chakra-heading",
    '[class*="chakra-heading"]',
    "h1, h2",
    'h1[class*="title"]',
    'h2[class*="title"]',
    'p[class*="title"]',
    'div[class*="title"]',
    '[data-testid*="product-name"]',
    '[data-testid*="product-title"]',
)
_PRICE_SELECTORS = (
    "p.chakra-text.css-1enygfq",
    "p[class*='1enygfq'], p[class*='1hulv5q']",
)
_ALT_PRICE_SELECTORS = (
    'p[class*="price"]',
    'span[class*="price"]',
    'div[class*="price"]',
    '[data-testid*="price"]',
    "div.css-c30f99 p.chakra-text",
    "div.css-0 p.chakra-text",
    'div[class*="css-0"] p[class*="chakra-text"]',
)
_AVAILABILITY_SELECTORS = ('span.chakra-badge.css-1dvt0g7', 'span[class*="1dvt0g7"]')
_STOCK_SELECTORS = (
    'p[class*="1yd6l9q"]',
    'span[class*="1yd6l9q"]',
    'div[class*="1yd6l9q"]',
    '[data-testid*="stock"]',
    '[data-testid*="balance"]',
)
_HISTORY_TYPE_SELECTOR = "span.chakra-badge.css-4yapew, span.chakra-badge.css-1kghjv8"

# Textos são lidos com innerText, igual ao inner_text() do Playwright.
_INITIAL_SNAPSHOT_JS = """(sel) => {
  const text = (el) => (el ? el.innerText.trim() : "");
  const firstText = (selector) => text(document.querySelector(selector));
  return {
    hasPasswordInput: document.querySelector('input[type="password"]') !== null,
    title: document.title,
    bodyText: document.body.innerText,
    nameCandidates: sel.names.map(firstText),
    skuEanText: firstText(sel.skuEan),
    priceCandidates: sel.prices.map(firstText),
    altPriceCandidates: sel.altPrices.map(firstText),
    availabilityCandidates: sel.availability.map(firstText),
    description: firstText(sel.description),
  };
}"""

_DETAILS_SNAPSHOT_JS = """(sel) => {
  const text = (el) => (el ? el.innerText.trim() : "");
  const firstText = (selector) => text(document.querySelector(selector));
  const history = Array.from(document.querySelectorAll("div.css-2p27im")).map((row) => ({
    type: text(row.querySelector(sel.historyType)),
    quantity: text(row.querySelector("p.chakra-text.css-1yd6l9q")),
    date: text(row.querySelector("p.chakra-text.css-1dv5bo2")),
    row_text: row.innerText.trim(),
  }));
  const specRows = Array.from(document.querySelectorAll("div.css-tuph3t")).map((row) => {
    const label = row.querySelector("p.css-1wld651");
    const value = row.querySelector("p.css-nidmuk");
    return label && value ? [text(label), text(value)] : null;
  }).filter((pair) => pair !== null);
  return {
    history,
    specRows,
    stockCandidates: sel.stock.map(firstText),
  };
}"""


class ProductNotLoadedError(RuntimeError):
    """A página abriu sem nome nem preço; não é gravado para não salvar um produto vazio."""


@dataclass(frozen=True)
class ProductJob:
    """Um produto a ser lido: ID, endereço e categoria."""

    product_id: str
    url: str
    category_name: str


def _context_destroyed(exc: Exception) -> bool:
    return "Execution context was destroyed" in str(exc)


class ProductReader:
    """Lê produtos usando uma página do navegador. Não é compartilhável entre tarefas."""

    def __init__(self, page: Page):
        self._page = page

    async def read(self, job: ProductJob) -> dict[str, Any]:
        for attempt in range(1, PRODUCT_READ_ATTEMPTS + 1):
            try:
                return await self._read_once(job)
            except SessionExpiredError:
                raise
            except ProductNotLoadedError:
                if attempt == PRODUCT_READ_ATTEMPTS:
                    raise
                log_progress(f"  Produto {job.product_id} ainda não carregou; recarregando ({attempt}/{PRODUCT_READ_ATTEMPTS})...")
            except Exception as exc:
                if not _context_destroyed(exc) or attempt == PRODUCT_READ_ATTEMPTS:
                    raise
                log_progress(
                    f"  Contexto destruído ao carregar produto {job.product_id}, "
                    f"tentando novamente ({attempt}/{PRODUCT_READ_ATTEMPTS})..."
                )
                await self._page.wait_for_timeout(1000)
        raise RuntimeError("Limite de tentativas excedido.")  # pragma: no cover

    async def _read_once(self, job: ProductJob) -> dict[str, Any]:
        page = self._page
        await page.goto(job.url, wait_until="domcontentloaded")
        await self._wait_for_content()

        initial = await self._loaded_snapshot()
        if initial["hasPasswordInput"]:
            raise SessionExpiredError()
        if not _has_name_or_price(initial):
            raise ProductNotLoadedError(job.product_id)

        body_after_stock = None
        if await _activate_tab(page, STOCK_TAB_NAME):
            body_after_stock = await page.evaluate("() => document.body.innerText")
        await _activate_tab(page, HISTORY_TAB_NAME)
        if not _mentions_cnpj(initial["bodyText"], body_after_stock):
            # O CNPJ do fornecedor chega depois do resto da página; uma releitura basta.
            await page.wait_for_timeout(_CNPJ_RETRY_WAIT_MS)
            body_after_stock = await page.evaluate("() => document.body.innerText")
        details = await page.evaluate(
            _DETAILS_SNAPSHOT_JS, {"historyType": _HISTORY_TYPE_SELECTOR, "stock": list(_STOCK_SELECTORS)}
        )

        snapshot = PageSnapshot(
            title=initial["title"],
            body_text=initial["bodyText"],
            name_candidates=tuple(initial["nameCandidates"]),
            sku_ean_text=initial["skuEanText"],
            price_candidates=tuple(initial["priceCandidates"]),
            alt_price_candidates=tuple(initial["altPriceCandidates"]),
            availability_candidates=tuple(initial["availabilityCandidates"]),
            description=initial["description"],
            spec_rows=tuple((label, value) for label, value in details["specRows"]),
            stock_candidates=tuple(details["stockCandidates"]),
            history_rows=tuple(details["history"]),
            body_text_after_stock_tab=body_after_stock,
        )
        return build_product_record(job.product_id, job.url, job.category_name, snapshot)

    async def _loaded_snapshot(self) -> dict[str, Any]:
        """Espera o nome ou o preço aparecerem e lê o DOM; páginas lentas ainda estão em esqueleto."""
        try:
            await self._page.wait_for_function(_PRODUCT_LOADED_JS, timeout=_LOAD_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            pass  # o chamador decide: sem nome nem preço, a leitura é repetida
        return await self._page.evaluate(_INITIAL_SNAPSHOT_JS, _initial_selectors())

    async def _wait_for_content(self) -> None:
        try:
            await self._page.wait_for_selector(READY_SELECTOR, state="visible", timeout=8000)
        except PlaywrightTimeoutError:
            await self._page.wait_for_timeout(1000)


def _mentions_cnpj(*texts: str | None) -> bool:
    return any(text and "CNPJ" in text for text in texts)


def _has_name_or_price(snapshot: dict[str, Any]) -> bool:
    texts = [*snapshot["nameCandidates"], *snapshot["priceCandidates"], *snapshot["altPriceCandidates"]]
    return any(texts)


def _initial_selectors() -> dict[str, Any]:
    return {
        "names": list(_NAME_SELECTORS),
        "skuEan": "p.chakra-text.css-nk7nkj",
        "prices": list(_PRICE_SELECTORS),
        "altPrices": list(_ALT_PRICE_SELECTORS),
        "availability": list(_AVAILABILITY_SELECTORS),
        "description": '[role="tabpanel"]',
    }


_PANEL_VISIBLE_JS = """(tab) => {
  const panel = document.getElementById(tab.getAttribute("aria-controls") || "");
  return !!panel && !panel.hidden && panel.offsetParent !== null && panel.innerText.trim().length > 0;
}"""


async def _activate_tab(page: Page, name: re.Pattern[str]) -> bool:
    """Seleciona a aba e espera o painel dela ficar visível. Retorna False se a aba não existir.

    innerText só devolve o texto como aparece na tela (ex.: SAÍDA em maiúsculas)
    quando o painel já está visível; por isso a espera é pelo painel, não por um tempo fixo.
    """
    tab = page.get_by_role("tab", name=name).first
    if not await tab.count():
        return False
    handle = await tab.element_handle()
    if await handle.get_attribute("aria-selected") == "true":
        return True
    await tab.click()
    try:
        await page.wait_for_function(_PANEL_VISIBLE_JS, arg=handle, timeout=TAB_CONTENT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        # Abas sem painel identificável seguem com o conteúdo que já está na tela.
        pass
    return True
