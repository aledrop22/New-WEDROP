"""Authenticate, map the full WeDrop catalog, and persist daily stock history."""

from __future__ import annotations

import asyncio
import argparse
import getpass
import json
import logging
import os
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from sales_reporting import (
    SalesRepository,
    SupabaseRepository,
    load_local_environment,
)


BASE_URL = "https://dash.wedrop.com.br"
PRODUCTS_PER_PAGE = 100
PROJECT_DIR = Path(__file__).resolve().parent
STORAGE_STATE_FILE = PROJECT_DIR / "storage_state.json"
DB_FILE = PROJECT_DIR / "wedrop_monitoramento.db"
JSON_DATA_FILE = PROJECT_DIR / "data.json"
LOG_FILE = PROJECT_DIR / "scraper_runs.log"
CATEGORY_SELECTOR = 'a[draggable="false"][data-group=""]'
PROGRESS_LOGGER = logging.getLogger("wedrop.scraper")
PRODUCT_PATH = re.compile(
    r"/catalog/(?:[^/?#]+/)*(?:"
    r"(\d+)|([0-9a-f]{8}-[0-9a-f-]{27,})"
    r")(?:/[^/?#]+)?/?$",
    re.IGNORECASE,
)
PRODUCT_FIELDS = (
    "sku",
    "ean",
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
    "total_stock_count",
    "real_balance",
)


def configure_progress_logging() -> None:
    PROGRESS_LOGGER.setLevel(logging.INFO)
    PROGRESS_LOGGER.propagate = False
    if PROGRESS_LOGGER.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    PROGRESS_LOGGER.addHandler(file_handler)
    PROGRESS_LOGGER.addHandler(console_handler)


def log_progress(message: str) -> None:
    PROGRESS_LOGGER.info(message)


class ProductJSONLWriter:
    """Write complete product batches to the legacy-compatible data.json file."""

    def __init__(self, output_path: Path):
        self.output_path = output_path

    def start(self) -> None:
        self.output_path.write_text("", encoding="utf-8")

    def append_batch(
        self, products: list[dict], captured_at: str
    ) -> None:
        records = []
        for product in products:
            record = dict(product)
            record["title"] = product.get("name", "")
            record["numero_vendas"] = product.get("number_sales", "")
            record["scrape_time"] = captured_at
            record["altura"] = product.get("height", "")
            record["largura"] = product.get("width", "")
            record["comprimento"] = product.get("length", "")
            record["peso"] = product.get("weight", "")
            records.append(json.dumps(record, ensure_ascii=False))

        with self.output_path.open("a", encoding="utf-8", newline="\n") as output:
            output.write("\n".join(records) + "\n")
            output.flush()
            os.fsync(output.fileno())


def product_id_from_url(url: str) -> str:
    match = PRODUCT_PATH.search(urlparse(url).path)
    return next((group for group in match.groups() if group), "") if match else ""


def value_for_label(text: str, labels: tuple[str, ...]) -> str:
    alternatives = "|".join(re.escape(label) for label in labels)
    match = re.search(
        rf"^\s*(?:{alternatives})\s*:?\s*(.+?)\s*$", text, re.IGNORECASE | re.MULTILINE
    )
    return match.group(1).strip() if match else ""


async def extract_technical_specs(page) -> dict[str, str]:
    specs = {}
    label_fields = {
        "ncm": "ncm",
        "peso": "weight",
        "altura": "height",
        "largura": "width",
        "comprimento": "length",
        "descrição": "description",
    }
    rows = page.locator("div.css-tuph3t")
    for row in await rows.all():
        label_node = row.locator("p.css-1wld651").first
        value_node = row.locator("p.css-nidmuk").first
        if not await label_node.count() or not await value_node.count():
            continue
        label = (await label_node.inner_text()).strip().casefold().rstrip(":")
        field = label_fields.get(label)
        if field:
            specs[field] = (await value_node.inner_text()).strip()
    return specs


def _as_int(value: str) -> int | None:
    match = re.search(r"\d[\d.,]*", value)
    if not match:
        return None
    return int(re.sub(r"\D", "", match.group()))


def _sales_count(value: str) -> str:
    match = re.fullmatch(r"\s*(\d[\d.,]*)\s*", value)
    return str(int(re.sub(r"\D", "", match.group(1)))) if match else ""


def _credential_values(
    email: str | None,
    password: str | None,
    prompt_for_credentials: bool,
) -> tuple[str, str]:
    email = (email or os.environ.get("WEDROP_EMAIL", "")).strip()
    password = password or os.environ.get("WEDROP_PASSWORD", "")
    if email and password:
        return email, password
    if not prompt_for_credentials or not sys.stdin.isatty():
        raise RuntimeError(
            "É necessário autenticar no WeDrop. Configure WEDROP_EMAIL e "
            "WEDROP_PASSWORD no arquivo .env ou nas variáveis de ambiente."
        )
    if not email:
        email = input("E-mail do WeDrop: ").strip()
    if not password:
        password = getpass.getpass("Senha do WeDrop: ")
    if not email or not password:
        raise RuntimeError("E-mail e senha são obrigatórios para autenticar no WeDrop.")
    return email, password


class WedropMonitor:
    def __init__(self, database_path: Path = DB_FILE):
        self.repository = SalesRepository(database_path)

    async def ensure_authenticated(
        self,
        page,
        context,
        email: str | None = None,
        password: str | None = None,
        prompt_for_credentials: bool = True,
    ) -> None:
        await page.goto(f"{BASE_URL}/catalog", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        login_form = page.locator('input[type="password"]')
        if "/login" not in page.url and not await login_form.count():
            return

        login_email, login_password = _credential_values(
            email, password, prompt_for_credentials
        )
        await page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
        await page.locator('input[type="email"], input[name="email"]').first.fill(
            login_email
        )
        await page.locator('input[type="password"], input[name="password"]').first.fill(
            login_password
        )
        await page.locator('button[type="submit"]').click()
        try:
            await page.wait_for_function(
                "() => !location.pathname.includes('/login') && "
                "!document.querySelector('input[type=password]')",
                timeout=30_000,
            )
        except PlaywrightTimeoutError as exc:
            feedback = await page.locator('[role="alert"], [data-status="error"]').all_inner_texts()
            detail = " ".join(feedback).strip()
            raise RuntimeError(
                "O WeDrop não confirmou o login. Confira e-mail e senha"
                + (f": {detail}" if detail else ".")
            ) from exc

        await page.goto(f"{BASE_URL}/catalog", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        if await page.locator('input[type="password"]').count():
            raise RuntimeError("Login não autorizado pelo WeDrop; sessão não foi salva.")
        await context.storage_state(path=str(STORAGE_STATE_FILE))
        log_progress(f"Sessão autenticada salva em {STORAGE_STATE_FILE.name}.")

    async def get_categories(self, page) -> list[dict]:
        categories = []
        seen_urls = set()
        category_links = page.locator(CATEGORY_SELECTOR)
        try:
            await category_links.first.wait_for(state="visible", timeout=15000)
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                "O catálogo abriu, mas as categorias não apareceram após "
                f"15 segundos (URL: {page.url}; título: {await page.title()}). "
                "Confirme se a sessão está autenticada e se o catálogo terminou "
                "de carregar."
            ) from exc

        for link in await category_links.all():
            href = await link.get_attribute("href")
            name_node = link.locator("p").first
            name = (await name_node.inner_text()).strip() if await name_node.count() else ""
            if not name:
                name = (await link.inner_text()).strip()
            if not href or not name or href in seen_urls:
                continue

            count_node = link.locator('p[class*="1lser6l"]').first
            count_text = (
                (await count_node.inner_text()).strip()
                if await count_node.count()
                else ""
            )
            if not count_text:
                title = await link.get_attribute("title") or ""
                count_text = title.split("—", 1)[1] if "—" in title else ""
            count_match = re.search(r"\d[\d.,]*", count_text)
            categories.append(
                {
                    "name": name,
                    "url": urljoin(BASE_URL, href),
                    "count": _as_int(count_match.group()) if count_match else None,
                }
            )
            seen_urls.add(href)

        if not categories:
            raise RuntimeError(
                "Nenhuma categoria foi encontrada no catálogo autenticado. "
                "A coleta foi interrompida para não registrar um mapeamento vazio."
            )
        return categories

    @staticmethod
    def _filter_categories(
        categories: list[dict], category_filter: str | None
    ) -> list[dict]:
        if not category_filter:
            return categories
        needle = category_filter.casefold().strip()
        exact_matches = [
            category
            for category in categories
            if category["name"].casefold() == needle
        ]
        if exact_matches:
            return exact_matches
        matches = [
            category
            for category in categories
            if needle in category["name"].casefold()
        ]
        if not matches:
            raise RuntimeError(
                f"Nenhuma categoria corresponde a '{category_filter}'. "
                "Categorias disponíveis: "
                + ", ".join(category["name"] for category in categories)
            )
        return matches

    async def _product_links_on_page(self, page) -> dict[str, str]:
        hrefs = await page.locator('a[href*="/catalog/"]').evaluate_all(
            "(anchors) => anchors.map((anchor) => anchor.href)"
        )
        links = {}
        for href in hrefs:
            product_id = product_id_from_url(href)
            if product_id:
                links.setdefault(product_id, href)
        return links

    @staticmethod
    def _parse_pagination_state(text: str) -> tuple[int, int] | None:
        match = re.search(r"página\s+(\d+)\s+de\s+(\d+)", text, re.IGNORECASE)
        if not match:
            return None
        current_page, total_pages = (int(value) for value in match.groups())
        if total_pages < 1 or current_page < 1 or current_page > total_pages:
            return None
        return current_page, total_pages

    async def _pagination_state(self, page) -> tuple[int, int] | None:
        text = await page.locator("body").inner_text()
        return self._parse_pagination_state(text)

    @staticmethod
    def _next_page_state(
        current_url: str, expected_products: int | None
    ) -> tuple[int, int] | None:
        if expected_products is None:
            return None
        parsed_url = urlparse(current_url)
        query = parse_qs(parsed_url.query, keep_blank_values=True)
        try:
            current_page = int(query["page"][0])
            limit = int(query["limit"][0])
        except (KeyError, ValueError, IndexError):
            return None
        if current_page < 1 or limit < 1:
            return None

        total_pages = (expected_products + limit - 1) // limit
        if current_page >= total_pages:
            return None

        return current_page + 1, total_pages

    async def _set_products_per_page(
        self, page, expected_products: int | None = None
    ) -> None:
        select = page.locator("select.chakra-select").first
        await select.wait_for(state="visible", timeout=10000)
        if not await select.count():
            return
        if not await select.locator(
            f'option[value="{PRODUCTS_PER_PAGE}"]'
        ).count():
            return
        if await select.input_value() != str(PRODUCTS_PER_PAGE):
            await select.select_option(str(PRODUCTS_PER_PAGE))
            await page.wait_for_function(
                "(size) => new URL(location.href).searchParams.get('limit') === String(size)",
                arg=PRODUCTS_PER_PAGE,
            )
        expected_pages = (
            (expected_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
            if expected_products is not None
            else None
        )
        for _ in range(40):
            state = await self._pagination_state(page)
            if state is not None and (
                expected_pages is None or state == (1, expected_pages)
            ):
                return
            await page.wait_for_timeout(250)
        raise RuntimeError(
            "O seletor foi configurado para 100 produtos por página, mas o "
            "indicador de paginação não corresponde à quantidade esperada."
        )

    async def _next_page(self, page):
        selectors = (
            'a[rel="next"]',
            'button[aria-label*="next" i]',
            'a[aria-label*="next" i]',
            'button[aria-label*="próxima" i]',
            'a[aria-label*="próxima" i]',
            'button:has-text("Próxima")',
            'button:has-text("Próximo")',
            'a:has-text("Próxima")',
            'a:has-text("Próximo")',
        )
        next_button = page.get_by_role("button", name=">", exact=True).last
        if await next_button.count() and await next_button.is_visible():
            if await next_button.is_enabled():
                return next_button
        for selector in selectors:
            candidate = page.locator(selector).last
            if (
                await candidate.count()
                and await candidate.is_visible()
                and await candidate.is_enabled()
            ):
                    return candidate
        return None

    async def get_products_from_category(self, page, category: dict) -> dict[str, str]:
        await page.goto(category["url"], wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        await self._set_products_per_page(page, category.get("count"))
        products: dict[str, str] = {}
        seen_pages: set[tuple[str, tuple[str, ...]]] = set()

        for _ in range(500):
            unchanged_rounds = 0
            previous_count = -1
            for _ in range(30):
                page_links = await self._product_links_on_page(page)
                products.update(page_links)
                if len(page_links) == previous_count:
                    unchanged_rounds += 1
                    if unchanged_rounds >= 2:
                        break
                else:
                    unchanged_rounds = 0
                    previous_count = len(page_links)
                await page.mouse.wheel(0, 1200)
                await page.wait_for_timeout(250)

            pagination_state = await self._pagination_state(page)
            if pagination_state is not None:
                current_page, total_pages = pagination_state
                log_progress(f"Listagem: página {current_page} de {total_pages}.")
                if current_page >= total_pages:
                    break

            if category["count"] is not None and len(products) >= category["count"]:
                break

            signature = (
                str(pagination_state or page.url),
                tuple(sorted(await self._product_links_on_page(page))),
            )
            if signature in seen_pages:
                raise RuntimeError(
                    f"A paginação da categoria {category['name']} repetiu uma "
                    "página antes de concluir a coleta."
                )
            seen_pages.add(signature)
            next_button = await self._next_page(page)
            if next_button is None:
                expected_product_count = category.get("count")
                fallback_state = self._next_page_state(
                    page.url, expected_product_count
                )
                if (
                    fallback_state is not None
                    and expected_product_count is not None
                    and len(products) < expected_product_count
                ):
                    expected_page, total_pages = fallback_state
                    numbered_button = page.get_by_role(
                        "button", name=str(expected_page), exact=True
                    ).last
                    if (
                        await numbered_button.count()
                        and await numbered_button.is_visible()
                        and await numbered_button.is_enabled()
                    ):
                        log_progress(
                            "  Botão de próxima página indisponível; "
                            f"selecionando a página {expected_page}."
                        )
                        await numbered_button.click()
                        for _ in range(40):
                            state = await self._pagination_state(page)
                            page_links = await self._product_links_on_page(page)
                            if state == fallback_state and page_links:
                                break
                            await page.wait_for_timeout(250)
                        else:
                            raise RuntimeError(
                                f"Não foi possível confirmar a página "
                                f"{expected_page} de {total_pages} da categoria "
                                f"{category['name']} após clicar no número da página."
                            )
                        continue
                if (
                    pagination_state is not None
                    and pagination_state[0] < pagination_state[1]
                ):
                    raise RuntimeError(
                        f"A categoria {category['name']} informa a página "
                        f"{pagination_state[0]} de {pagination_state[1]}, mas o "
                        "botão para avançar está indisponível."
                    )
                if (
                    category["count"] is not None
                    and len(products) < category["count"]
                ):
                    raise RuntimeError(
                        f"A categoria {category['name']} informou "
                        f"{category['count']} produtos, mas só foram encontrados "
                        f"{len(products)} e não há próxima página."
                    )
                break
            previous_url = page.url
            previous_page = (
                pagination_state[0] if pagination_state is not None else None
            )
            await next_button.click()
            changed = False
            for _ in range(20):
                await page.wait_for_timeout(250)
                new_state = await self._pagination_state(page)
                if (
                    previous_page is not None
                    and new_state is not None
                    and new_state[0] > previous_page
                ):
                    changed = True
                    break
                if page.url != previous_url:
                    changed = True
                    break
            if not changed:
                raise RuntimeError(
                    f"Não foi possível confirmar a mudança de página na categoria "
                    f"{category['name']}."
                )
        else:
            raise RuntimeError(
                f"A coleta da categoria {category['name']} ultrapassou o limite "
                "de 500 páginas."
            )
        return products

    async def get_product_details_and_history(
        self, page, product_id: str, product_url: str, category_name: str
    ) -> dict:
        await page.goto(product_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        if await page.locator('input[type="password"]').count():
            raise RuntimeError(
                "A sessão WeDrop expirou durante a coleta. Execute novamente para "
                "autenticar e retomar o mapeamento."
            )

        name_node = page.locator("h1, h2").first
        name = (await name_node.inner_text()).strip() if await name_node.count() else ""
        if not name or name.casefold() in {"produto", "product"}:
            page_title = (await page.title()).strip()
            name = (
                page_title
                if page_title.casefold() not in {"wedrop", "produto", "product"}
                else ""
            )
        page_text = await page.locator("body").inner_text()

        sku_ean_node = page.locator('p[class*="nk7nkj"]').first
        sku_ean_text = (
            (await sku_ean_node.inner_text()).strip()
            if await sku_ean_node.count()
            else page_text
        )
        sku_match = re.search(r"SKU:\s*([^|]+)", sku_ean_text, re.IGNORECASE)
        ean_match = re.search(r"EAN:\s*([^|]+)", sku_ean_text, re.IGNORECASE)
        price_node = page.locator('p[class*="1enygfq"], p[class*="1hulv5q"]').first
        price = (await price_node.inner_text()).strip() if await price_node.count() else ""
        availability_node = page.locator('span[class*="1dvt0g7"]').first
        availability = (
            (await availability_node.inner_text()).strip()
            if await availability_node.count()
            else ""
        )
        description_panel = page.get_by_role("tabpanel").first
        description = (
            (await description_panel.inner_text()).strip()
            if await description_panel.count()
            else ""
        )

        history_tab = page.get_by_role("tab", name=re.compile("Histórico de Estoque", re.I))
        if await history_tab.count():
            await history_tab.first.click()
            await page.wait_for_timeout(400)

        history = []
        history_rows = page.locator(
            "div.css-2p27im, [data-testid*='history-row'], [class*='historyRow']"
        )
        for row in await history_rows.all():
            type_node = row.locator('span[class*="1kghjv8"]').first
            quantity_node = row.locator('p[class*="1yd6l9q"]').first
            date_node = row.locator('p[class*="1dv5bo2"]').first
            movement_type = (
                (await type_node.inner_text()).strip() if await type_node.count() else ""
            )
            quantity = (
                (await quantity_node.inner_text()).strip()
                if await quantity_node.count()
                else ""
            )
            event_date = (
                (await date_node.inner_text()).strip() if await date_node.count() else ""
            )
            row_text = (await row.inner_text()).strip()
            nf_match = re.search(r"Chave da NF:\s*(.+)", row_text, re.IGNORECASE)
            if movement_type and quantity:
                history.append(
                    {
                        "type": movement_type,
                        "quantity": quantity,
                        "date": event_date,
                        "nf_key": nf_match.group(1).strip() if nf_match else "",
                    }
                )

        details = await extract_technical_specs(page)
        cnpj = value_for_label(page_text, ("CNPJ", "CNPJ do fornecedor"))
        origin = value_for_label(page_text, ("Estado de origem", "Origem"))
        stock = value_for_label(
            page_text,
            ("Estoque", "Disponibilidade", "Saldo disponível", "Estoque disponível"),
        ) or availability
        real_balance = value_for_label(page_text, ("Saldo real", "Saldo"))
        total_stock = value_for_label(page_text, ("Estoque total", "Total em estoque"))
        sales = value_for_label(page_text, ("Vendas", "Número de vendas"))
        sales_count = _sales_count(sales) or _sales_count(
            details.get("number_sales", "")
        )
        status = value_for_label(page_text, ("Status", "Situação"))
        if not status and re.search(r"\b(desativado|inativo)\b", page_text, re.I):
            status = "Inativo"
        elif not status and re.search(r"\b(ativo|ativado)\b", page_text, re.I):
            status = "Ativo"

        return {
            "product_id": product_id,
            "name": name,
            "category": category_name,
            "url": product_url,
            "sku": sku_match.group(1).strip() if sku_match else details.get("sku", ""),
            "ean": ean_match.group(1).strip() if ean_match else details.get("ean", ""),
            "price": price or value_for_label(page_text, ("Preço",)),
            "availability": availability,
            "stock": stock,
            "total_stock_count": total_stock or details.get("total_stock_count", ""),
            "real_balance": real_balance or details.get("real_balance", ""),
            "is_active": status,
            "supplier": value_for_label(page_text, ("Fornecedor",)) or details.get("supplier", ""),
            "cnpj": cnpj or details.get("cnpj", ""),
            "origin_state": origin or details.get("origin_state", ""),
            "ncm": details.get("ncm", ""),
            "weight": details.get("weight", ""),
            "height": details.get("height", ""),
            "width": details.get("width", ""),
            "length": details.get("length", ""),
            "description": description or details.get("description", ""),
            "number_sales": sales_count,
            "stock_history": history,
        }

    async def run_full_mapping(
        self,
        email: str | None = None,
        password: str | None = None,
        prompt_for_credentials: bool = True,
        category_filter: str | None = None,
        product_limit: int | None = None,
        local_only: bool = False,
    ) -> None:
        configure_progress_logging()
        log_progress("Iniciando coleta completa do catálogo WeDrop.")
        log_progress(f"Destino JSON: {JSON_DATA_FILE}")
        log_progress(f"Destino histórico local: {DB_FILE}")
        load_local_environment()
        supabase = None if local_only else SupabaseRepository.from_environment()
        captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
        if supabase is not None:
            log_progress("Validando conexão e tabelas do Supabase antes da coleta.")
            supabase.validate()
            log_progress("Conexão e tabelas Supabase validadas.")
        else:
            log_progress("Modo local: Supabase não será atualizado.")
        async with async_playwright() as playwright:
            log_progress("Iniciando navegador Chromium.")
            browser = await playwright.chromium.launch(headless=True)
            try:
                if STORAGE_STATE_FILE.is_file():
                    context = await browser.new_context(
                        storage_state=str(STORAGE_STATE_FILE)
                    )
                else:
                    context = await browser.new_context()
                try:
                    page = await context.new_page()
                    await self.ensure_authenticated(
                        page, context, email, password, prompt_for_credentials
                    )
                    log_progress("Sessão autenticada e catálogo aberto.")
                    categories = self._filter_categories(
                        await self.get_categories(page), category_filter
                    )
                    log_progress(f"Categorias selecionadas: {len(categories)}.")
                    total_products = 0
                    json_writer = ProductJSONLWriter(JSON_DATA_FILE)
                    json_writer.start()
                    log_progress(
                        "data.json limpo para esta execução; histórico SQLite e "
                        "registros anteriores do Supabase serão preservados."
                    )
                    remaining_limit = product_limit

                    for category_index, category in enumerate(categories, 1):
                        log_progress(
                            f"[{category_index}/{len(categories)}] "
                            f"Lendo listagem da categoria {category['name']}..."
                        )
                        product_links = await self.get_products_from_category(
                            page, category
                        )
                        discovered_product_count = len(product_links)
                        expected_count = category.get("count")
                        log_progress(
                            f"Listagem lida: {discovered_product_count} produtos "
                            f"encontrados"
                            + (
                                f" de {expected_count} informados pelo site."
                                if expected_count is not None
                                else "."
                            )
                        )
                        if remaining_limit is not None:
                            product_links = dict(
                                list(product_links.items())[:remaining_limit]
                            )
                            remaining_limit -= len(product_links)
                            log_progress(
                                f"Limite aplicado: serão detalhados "
                                f"{len(product_links)} produtos nesta categoria."
                            )
                        self.repository.save_category(
                            category, len(product_links), captured_at
                        )
                        log_progress(
                            f"Categoria salva no SQLite: {category['name']} "
                            f"({len(product_links)} detalhados)."
                        )
                        if supabase is not None:
                            supabase.save_category(
                                category, len(product_links), captured_at
                            )
                            log_progress(
                                f"Categoria sincronizada no Supabase: "
                                f"{category['name']}."
                            )
                        products = []
                        for product_index, (product_id, product_url) in enumerate(
                            product_links.items(), 1
                        ):
                            log_progress(
                                f"Lendo produto {product_index}/{len(product_links)} "
                                f"(ID {product_id})."
                            )
                            product = await self.get_product_details_and_history(
                                page, product_id, product_url, category["name"]
                            )
                            products.append(product)
                            log_progress(
                                f"Produto lido: {product.get('name') or 'nome indisponível'}; "
                                f"histórico: {len(product.get('stock_history', []))} "
                                "movimentações."
                            )
                            if len(products) == 50:
                                log_progress("Salvando lote de 50 produtos no SQLite.")
                                self.repository.save_products(products, captured_at)
                                log_progress(
                                    "Lote de 50 produtos salvo no SQLite, incluindo "
                                    "históricos de estoque."
                                )
                                json_writer.append_batch(products, captured_at)
                                log_progress("Lote de 50 produtos gravado em data.json.")
                                if supabase is not None:
                                    log_progress(
                                        "Enviando lote de 50 produtos e históricos "
                                        "para o Supabase."
                                    )
                                    supabase.save_products(products, captured_at)
                                    log_progress(
                                        "Lote de 50 produtos e históricos confirmado "
                                        "no Supabase."
                                    )
                                total_products += len(products)
                                products = []
                        if products:
                            log_progress(
                                f"Salvando lote final de {len(products)} produtos "
                                "no SQLite."
                            )
                            self.repository.save_products(products, captured_at)
                            log_progress(
                                f"Lote final de {len(products)} produtos salvo no "
                                "SQLite, incluindo históricos de estoque."
                            )
                            json_writer.append_batch(products, captured_at)
                            log_progress(
                                f"Lote final de {len(products)} produtos gravado "
                                "em data.json."
                            )
                            if supabase is not None:
                                log_progress(
                                    f"Enviando lote final de {len(products)} produtos "
                                    "e históricos para o Supabase."
                                )
                                supabase.save_products(products, captured_at)
                                log_progress(
                                    f"Lote final de {len(products)} produtos e "
                                    "históricos confirmado no Supabase."
                                )
                            total_products += len(products)
                        if (
                            category["count"] is not None
                            and discovered_product_count < category["count"]
                        ):
                            log_progress(
                                f"AVISO: site informa {category['count']} itens; "
                                f"foram encontrados {discovered_product_count} links."
                            )
                        log_progress(
                            f"Categoria concluída: {len(product_links)} produtos "
                            "detalhados e salvos."
                        )
                        if remaining_limit == 0:
                            break

                    destination = "localmente" if local_only else "e sincronizado"
                    log_progress(
                        f"Mapeamento concluído {destination}: {len(categories)} "
                        f"categorias, {total_products} produtos."
                    )
                    log_progress(f"Destino histórico local: {DB_FILE}")
                    log_progress(f"Catálogo JSON Lines: {JSON_DATA_FILE}")
                    if supabase is not None:
                        log_progress(
                            "Destino remoto: Supabase (categorias, produtos e eventos)."
                        )
                    log_progress(f"Log detalhado da execução: {LOG_FILE}")
                finally:
                    await context.close()
            finally:
                if supabase is not None:
                    supabase.close()
                await browser.close()

    def close(self) -> None:
        self.repository.close()


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("o limite deve ser maior que zero")
    return parsed


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mapeia o catálogo autenticado do WeDrop."
    )
    parser.add_argument(
        "--category",
        help="Coleta apenas categorias cujo nome contenha este texto.",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        help="Limita o total de produtos detalhados nesta execução.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Grava no JSON e banco SQLite locais, sem sincronizar com Supabase.",
    )
    args = parser.parse_args()
    monitor = WedropMonitor()
    try:
        try:
            await monitor.run_full_mapping(
                category_filter=args.category,
                product_limit=args.limit,
                local_only=args.local_only,
            )
        except Exception:
            if PROGRESS_LOGGER.handlers:
                PROGRESS_LOGGER.exception("Coleta WeDrop encerrada com erro.")
            raise
    finally:
        monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
