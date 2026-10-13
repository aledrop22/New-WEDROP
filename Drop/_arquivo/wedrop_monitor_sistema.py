"""Authenticate, map the full WeDrop catalog, and persist daily stock history."""

from __future__ import annotations

import asyncio
import argparse
import getpass
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from product_naming import clean_product_name
from sales_reporting import (
    SalesRepository,
    SupabaseRepository,
    load_local_environment,
)


BASE_URL = "https://dash.wedrop.com.br"
PRODUCTS_PER_PAGE = 100
# Quantas vezes repetir a leitura da listagem quando o site informa mais
# produtos do que os links encontrados.
LISTING_RETRIES = 2
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


def calculate_current_balance(stock_history: list[dict]) -> int:
    """Calcula o saldo atual baseado no histórico de movimentações.

    Lógica:
    1. Se houver um saldo positivo no histórico, usa como base
    2. Soma todas as entradas (+unidades)
    3. Subtrai todas as saídas (-unidades)
    4. Retorna o saldo calculado
    """
    if not stock_history:
        return 0

    balance = 0
    has_initial_balance = False

    # Verificar se há um saldo inicial no histórico
    for movement in stock_history:
        quantity = movement.get("quantity", "")
        movement_type = movement.get("type", "").upper()

        # Se não for entrada/saída e tem número, pode ser saldo inicial
        if movement_type not in {"ENTRADA", "SAÍDA", "SAIDA"}:
            qty_match = re.search(r"\d+", quantity)
            if qty_match:
                qty = int(qty_match.group())
                # Se for positivo e não tem + ou -, usa como saldo inicial
                if qty > 0 and "+" not in quantity and "-" not in quantity:
                    balance = qty
                    has_initial_balance = True
                    break

    # Calcular baseado em entradas e saídas
    for movement in stock_history:
        quantity = movement.get("quantity", "")
        movement_type = movement.get("type", "").upper()

        if movement_type == "ENTRADA":
            qty_match = re.search(r"\d+", quantity)
            if qty_match:
                balance += int(qty_match.group())
        elif movement_type in {"SAÍDA", "SAIDA"}:
            qty_match = re.search(r"\d+", quantity)
            if qty_match:
                balance -= int(qty_match.group())

    return balance


def load_collected_product_ids(json_path: Path) -> set[str]:
    """Carrega os IDs de produtos já gravados em data.json (JSON Lines)."""
    collected_ids: set[str] = set()
    if not json_path.is_file():
        return collected_ids
    with json_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            product_id = record.get("product_id")
            if product_id:
                collected_ids.add(str(product_id))
    return collected_ids


def backup_data_file(json_path: Path) -> Path | None:
    """Cria uma cópia de segurança do data.json antes de iniciar a coleta.

    Retorna o caminho do backup criado, ou None se não havia arquivo para
    copiar. O backup é nomeado com timestamp e fica na mesma pasta.
    """
    if not json_path.is_file():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = json_path.with_name(f"data_backup_{timestamp}.json")
    shutil.copy2(json_path, backup_path)
    log_progress(f"Backup de segurança criado: {backup_path.name}")
    return backup_path


def restore_missing_from_backups(
    json_path: Path, exclude: set[Path] | None = None, backup_limit: int = 5
) -> int:
    """Acrescenta ao data.json os produtos que só existem nos backups recentes.

    Nunca reescreve nem remove registros: apenas anexa product_id ausentes,
    começando pelo backup mais recente. Assim, se o data.json foi truncado,
    a retomada não repete produtos que já estão salvos em um backup.
    Retorna a quantidade de registros restaurados.
    """
    exclude = exclude or set()
    collected = load_collected_product_ids(json_path)
    candidates = [
        path
        for path in sorted(
            json_path.parent.glob("data_backup*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if path != json_path and path not in exclude
    ][:backup_limit]

    new_lines: list[str] = []
    for backup in candidates:
        with backup.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                product_id = str(record.get("product_id") or "")
                if product_id and product_id not in collected:
                    collected.add(product_id)
                    new_lines.append(stripped)

    if not new_lines:
        return 0
    needs_newline = (
        json_path.is_file()
        and json_path.stat().st_size > 0
        and not json_path.read_bytes().endswith(b"\n")
    )
    with json_path.open("a", encoding="utf-8", newline="\n") as output:
        if needs_newline:
            output.write("\n")
        output.write("\n".join(new_lines) + "\n")
        output.flush()
        os.fsync(output.fileno())
    log_progress(
        f"{len(new_lines)} produtos restaurados de backups recentes para "
        "data.json (registros existentes não foram alterados)."
    )
    return len(new_lines)


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
        # Verifica se já está autenticado (não está na página de login e não
        # há campo de senha). Usa try/except pois a página pode navegar/redirecionar.
        try:
            has_login_field = await page.locator('input[type="password"]').count() > 0
        except Exception:
            has_login_field = False
        if "/login" not in page.url and not has_login_field:
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
                log_progress(
                    f"Listagem: página {current_page} de {total_pages}; "
                    f"{len(products)} produtos acumulados."
                )
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
                    log_progress(
                        f"AVISO: A categoria {category['name']} informou "
                        f"{category['count']} produtos, mas só foram encontrados "
                        f"{len(products)} e não há próxima página. "
                        "Continuando com os produtos encontrados."
                    )
                break
            if pagination_state is None:
                raise RuntimeError(
                    f"Não foi possível ler a página atual da categoria "
                    f"{category['name']}."
                )
            previous_page = pagination_state[0]
            target_page = previous_page + 1
            previous_links = set(await self._product_links_on_page(page))
            # Vai para a página seguinte pelo número; se não houver, usa ">".
            numbered_button = page.get_by_role(
                "button", name=str(target_page), exact=True
            ).first
            if await numbered_button.count() and await numbered_button.is_enabled():
                await numbered_button.click()
            else:
                await next_button.click()
            changed = False
            for _ in range(40):
                await page.wait_for_timeout(250)
                new_state = await self._pagination_state(page)
                if new_state is None:
                    continue
                if new_state[0] > target_page:
                    raise RuntimeError(
                        f"A paginação da categoria {category['name']} pulou da "
                        f"página {previous_page} para {new_state[0]}."
                    )
                if (
                    new_state[0] == target_page
                    and set(await self._product_links_on_page(page)) != previous_links
                ):
                    changed = True
                    break
            if not changed:
                raise RuntimeError(
                    f"Não foi possível confirmar a página {target_page} da "
                    f"categoria {category['name']}."
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
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await page.goto(product_url, wait_until="domcontentloaded")
                # Aguardar conteúdo da página carregar (nome ou preço aparecem)
                try:
                    await page.wait_for_selector(
                        "h2.chakra-heading, p.chakra-text.css-1enygfq, "
                        "p[class*='1enygfq'], p[class*='1hulv5q']",
                        state="visible",
                        timeout=8000,
                    )
                except Exception:
                    # Fallback: esperar um pouco mais para a página renderizar
                    await page.wait_for_timeout(1500)
                if await page.locator('input[type="password"]').count():
                    raise RuntimeError(
                        "A sessão WeDrop expirou durante a coleta. Execute novamente para "
                        "autenticar e retomar o mapeamento."
                    )

                # Tentar múltiplas fontes para o nome do produto - seletores específicos primeiro
                name = ""

                # Seletores específicos do WeDrop (prioridade máxima)
                specific_selectors = [
                    'h2.chakra-heading.css-18puvtl',
                    'h1.chakra-heading',
                    'h2.chakra-heading',
                    '[class*="chakra-heading"]',
                ]

                for selector in specific_selectors:
                    name_node = page.locator(selector).first
                    if await name_node.count():
                        candidate = (await name_node.inner_text()).strip()
                        if candidate and candidate.casefold() not in {"produto", "product", "wedrop"}:
                            name = candidate
                            break

                # Se não encontrou, tentar seletores genéricos
                if not name or name.casefold() in {"produto", "product"}:
                    name_node = page.locator("h1, h2").first
                    name = (await name_node.inner_text()).strip() if await name_node.count() else ""

                # Se ainda não encontrou, tentar outros seletores
                if not name or name.casefold() in {"produto", "product"}:
                    alternative_selectors = [
                        'h1[class*="title"]',
                        'h2[class*="title"]',
                        'p[class*="title"]',
                        'div[class*="title"]',
                        '[data-testid*="product-name"]',
                        '[data-testid*="product-title"]',
                    ]
                    for selector in alternative_selectors:
                        alt_node = page.locator(selector).first
                        if await alt_node.count():
                            alt_name = (await alt_node.inner_text()).strip()
                            if alt_name and alt_name.casefold() not in {"produto", "product", "wedrop"}:
                                name = alt_name
                                break

                # Se ainda não tem nome, tentar do título da página
                if not name or name.casefold() in {"produto", "product"}:
                    page_title = (await page.title()).strip()
                    # Remove prefixos comuns de WEDROP
                    page_title = re.sub(r"^(?:we\s*drop|wedrop|we-drop)\s*[-–:]?\s*", "", page_title, flags=re.IGNORECASE)
                    name = (
                        page_title
                        if page_title.casefold() not in {"wedrop", "produto", "product"}
                        else ""
                    )

                page_text = await page.locator("body").inner_text()

                sku_ean_node = page.locator('p.chakra-text.css-nk7nkj').first
                sku_ean_text = (
                    (await sku_ean_node.inner_text()).strip()
                    if await sku_ean_node.count()
                    else page.locator('p[class*="nk7nkj"]').first
                )
                if await sku_ean_node.count():
                    sku_ean_text = (await sku_ean_node.inner_text()).strip()
                else:
                    sku_ean_text = page_text
                break
            except Exception as e:
                if "Execution context was destroyed" in str(e) and attempt < max_retries - 1:
                    log_progress(f"  Contexto destruído ao carregar produto {product_id}, tentando novamente ({attempt + 1}/{max_retries})...")
                    await page.wait_for_timeout(1000)
                    continue
                raise
        sku_match = re.search(r"SKU:\s*([^|]+)", sku_ean_text, re.IGNORECASE)
        ean_match = re.search(r"EAN:\s*([^|]+)", sku_ean_text, re.IGNORECASE)

        # Preço - seletor específico
        price_node = page.locator('p.chakra-text.css-1enygfq').first
        price = (await price_node.inner_text()).strip() if await price_node.count() else ""
        if not price:
            price_node = page.locator('p[class*="1enygfq"], p[class*="1hulv5q"]').first
            price = (await price_node.inner_text()).strip() if await price_node.count() else ""

        # Tentar extrair preço de outros seletores se o principal falhar
        if not price:
            alternative_price_selectors = [
                'p[class*="price"]',
                'span[class*="price"]',
                'div[class*="price"]',
                '[data-testid*="price"]',
                # Seletor baseado na estrutura informada pelo usuário
                'div.css-c30f99 p.chakra-text',
                'div.css-0 p.chakra-text',
                'div[class*="css-0"] p[class*="chakra-text"]',
            ]
            for selector in alternative_price_selectors:
                alt_price_node = page.locator(selector).first
                if await alt_price_node.count():
                    alt_price = (await alt_price_node.inner_text()).strip()
                    if re.search(r'R\$\s*[\d.,]+', alt_price):
                        price = alt_price
                        break

        # Último recurso: procurar por "R$" no texto completo da página
        if not price:
            price_matches = re.findall(r'R\$\s*[\d]{1,3}(?:\.[\d]{3})*(?:,[\d]{2})?', page_text)
            if price_matches:
                # Pega o primeiro valor monetário encontrado (normalmente é o preço)
                price = price_matches[0].strip()

        # Disponibilidade/Ativo - seletor específico
        availability_node = page.locator('span.chakra-badge.css-1dvt0g7').first
        availability = (
            (await availability_node.inner_text()).strip()
            if await availability_node.count()
            else ""
        )
        if not availability:
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

        # Clicar na aba de valores/estoque para capturar o saldo antes do histórico
        stock_tab = page.get_by_role("tab", name=re.compile("(Valores|Estoque|Saldo)", re.I))
        if await stock_tab.count():
            await stock_tab.first.click()
            await page.wait_for_timeout(400)
            # Atualizar page_text após clicar na aba de estoque
            page_text = await page.locator("body").inner_text()

        history_tab = page.get_by_role("tab", name=re.compile("Histórico de Estoque", re.I))
        if await history_tab.count():
            await history_tab.first.click()
            await page.wait_for_timeout(400)

        history = []
        # Seletores específicos para histórico de estoque
        history_rows = page.locator('div.css-2p27im')
        for row in await history_rows.all():
            type_node = row.locator('span.chakra-badge.css-4yapew, span.chakra-badge.css-1kghjv8').first
            quantity_node = row.locator('p.chakra-text.css-1yd6l9q').first
            date_node = row.locator('p.chakra-text.css-1dv5bo2').first
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

        # Se não houver histórico, adicionar mensagem informativa
        if not history:
            history.append({
                "type": "NÃO HOUVE MOVIMENTAÇÃO DE SALDO",
                "quantity": "",
                "date": "",
                "nf_key": ""
            })

        # Calcular saldo atual baseado no histórico
        calculated_balance = calculate_current_balance(history)

        details = await extract_technical_specs(page)
        cnpj = value_for_label(page_text, ("CNPJ", "CNPJ do fornecedor"))
        origin = value_for_label(page_text, ("Estado de origem", "Origem"))

        # Tentar extrair saldo de múltiplas fontes
        stock_value = ""
        real_balance_value = ""
        total_stock_value = ""

        # Tentar buscar saldo numérico em vários seletores
        stock_selectors = [
            'p[class*="1yd6l9q"]',
            'span[class*="1yd6l9q"]',
            'div[class*="1yd6l9q"]',
            '[data-testid*="stock"]',
            '[data-testid*="balance"]',
        ]

        for selector in stock_selectors:
            stock_node = page.locator(selector).first
            if await stock_node.count():
                stock_text = (await stock_node.inner_text()).strip()
                # Verificar se é um número (saldo) e não apenas "DISPONÍVEL"
                if re.search(r'\d+', stock_text) and stock_text not in {"DISPONÍVEL", "INDISPONÍVEL"}:
                    stock_value = stock_text
                    break

        # Se não encontrou nos seletores, usar labels de texto
        if not stock_value:
            stock_value = value_for_label(
                page_text,
                ("Estoque", "Disponibilidade", "Saldo disponível", "Estoque disponível"),
            ) or availability

        # Usar saldo calculado se não encontrou na página
        if not stock_value or stock_value in {"DISPONÍVEL", "INDISPONÍVEL"}:
            if calculated_balance > 0:
                stock_value = str(calculated_balance)

        stock = stock_value
        real_balance = value_for_label(page_text, ("Saldo real", "Saldo")) or str(calculated_balance) if calculated_balance > 0 else stock_value
        total_stock = value_for_label(page_text, ("Estoque total", "Total em estoque")) or str(calculated_balance) if calculated_balance > 0 else stock_value
        sales = value_for_label(page_text, ("Vendas", "Número de vendas"))
        sales_count = _sales_count(sales) or _sales_count(
            details.get("number_sales", "")
        )
        status = value_for_label(page_text, ("Status", "Situação"))
        if not status and re.search(r"\b(desativado|inativo)\b", page_text, re.I):
            status = "Inativo"
        elif not status and re.search(r"\b(ativo|ativado)\b", page_text, re.I):
            status = "Ativo"

        # Tentar extrair nome com limpeza
        product_name = clean_product_name(name, description or details.get("description", ""))

        # Se ainda não tem nome, usar fallbacks
        if not product_name or len(product_name) < 3:
            # Tentar usar SKU como nome
            sku_value = sku_match.group(1).strip() if sku_match else details.get("sku", "")
            if sku_value:
                product_name = f"Produto {sku_value}"
            else:
                # Último recurso: usar ID e categoria
                product_name = f"Produto {product_id} ({category_name})"

        return {
            "product_id": product_id,
            "name": product_name,
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
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-logging",
                    "--log-level=0",
                    "--disable-dev-shm-usage",
                ],
            )
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

                    # Backup do data.json ANTES de qualquer alteração
                    current_backup = backup_data_file(JSON_DATA_FILE)

                    total_products = 0
                    json_writer = ProductJSONLWriter(JSON_DATA_FILE)
                    restore_missing_from_backups(
                        JSON_DATA_FILE,
                        exclude={current_backup} if current_backup else None,
                    )
                    collected_ids = load_collected_product_ids(JSON_DATA_FILE)
                    if collected_ids:
                        log_progress(
                            f"data.json preservado com {len(collected_ids)} produtos "
                            "já coletados. A coleta vai continuar de onde parou, "
                            "ignorando os produtos já registrados."
                        )
                    else:
                        json_writer.start()
                        log_progress(
                            "data.json vazio; iniciando coleta completa. "
                            "histórico SQLite e registros anteriores do Supabase "
                            "serão preservados."
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
                        expected_count = category.get("count")
                        # O site é a referência: se faltaram links, repete a leitura
                        # da listagem e junta o que foi encontrado nas tentativas.
                        for retry in range(1, LISTING_RETRIES + 1):
                            if expected_count is None or len(product_links) >= expected_count:
                                break
                            log_progress(
                                f"  Listagem divergente: {len(product_links)} de "
                                f"{expected_count} produtos; repetindo a leitura "
                                f"({retry}/{LISTING_RETRIES})."
                            )
                            try:
                                retried_links = await self.get_products_from_category(
                                    page, category
                                )
                            except RuntimeError as exc:
                                log_progress(
                                    f"  Nova leitura falhou ({exc}); mantendo "
                                    f"{len(product_links)} links já encontrados."
                                )
                                break
                            product_links = {**product_links, **retried_links}
                        discovered_product_count = len(product_links)
                        log_progress(
                            f"Listagem lida: {discovered_product_count} produtos "
                            f"encontrados"
                            + (
                                f" de {expected_count} informados pelo site."
                                if expected_count is not None
                                else "."
                            )
                        )
                        if collected_ids:
                            before = len(product_links)
                            product_links = {
                                pid: url
                                for pid, url in product_links.items()
                                if pid not in collected_ids
                            }
                            skipped = before - len(product_links)
                            if skipped:
                                log_progress(
                                    f"  {skipped} produtos já coletados nesta "
                                    f"categoria; restam {len(product_links)}."
                                )
                            if not product_links:
                                log_progress(
                                    f"  Categoria {category['name']} já completa; "
                                    "pulando."
                                )
                                continue
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

                        def _flush_batch(batch: list[dict]) -> None:
                            """Grava o lote atual no SQLite, JSON e Supabase."""
                            nonlocal total_products
                            if not batch:
                                return
                            label = f"lote de {len(batch)} produtos"
                            log_progress(f"Salvando {label} no SQLite.")
                            self.repository.save_products(batch, captured_at)
                            log_progress(
                                f"{label.capitalize()} salvo no SQLite, "
                                "incluindo históricos de estoque."
                            )
                            json_writer.append_batch(batch, captured_at)
                            log_progress(f"{label.capitalize()} gravado em data.json.")
                            if supabase is not None:
                                log_progress(
                                    f"Enviando {label} e históricos para o Supabase."
                                )
                                supabase.save_products(batch, captured_at)
                                log_progress(
                                    f"{label.capitalize()} e históricos confirmado "
                                    "no Supabase."
                                )
                            total_products += len(batch)

                        try:
                            for product_index, (product_id, product_url) in enumerate(
                                product_links.items(), 1
                            ):
                                # Pular produtos já coletados (retomada de onde parou)
                                if product_id in collected_ids:
                                    continue
                                log_progress(
                                    f"Lendo produto {product_index}/{len(product_links)} "
                                    f"(ID {product_id})."
                                )
                                try:
                                    product = await self.get_product_details_and_history(
                                        page, product_id, product_url, category["name"]
                                    )
                                except RuntimeError as exc:
                                    if "sessão wedrop expirou" not in str(
                                        exc
                                    ).casefold() and "sessao wedrop expirou" not in str(
                                        exc
                                    ).casefold():
                                        raise
                                    log_progress(
                                        f"  Sessão expirou no produto {product_id}; "
                                        "salvando progresso e reautenticando..."
                                    )
                                    _flush_batch(products)
                                    products = []
                                    await self.ensure_authenticated(
                                        page,
                                        context,
                                        email,
                                        password,
                                        prompt_for_credentials,
                                    )
                                    log_progress("  Sessão reestabelecida; retomando coleta.")
                                    product = await self.get_product_details_and_history(
                                        page, product_id, product_url, category["name"]
                                    )
                                products.append(product)
                                # Validar campos obrigatórios
                                missing_fields = []
                                if not product.get("name") or len(product.get("name", "")) < 3:
                                    missing_fields.append("nome")
                                if not product.get("price"):
                                    missing_fields.append("preço")
                                if not product.get("availability"):
                                    missing_fields.append("disponibilidade")

                                if missing_fields:
                                    log_progress(
                                        f"⚠️ Campos obrigatórios vazios: {', '.join(missing_fields)} "
                                        f"(ID {product_id})"
                                    )

                                log_progress(
                                    f"Produto lido: {product.get('name') or 'nome indisponível'}; "
                                    f"histórico: {len(product.get('stock_history', []))} "
                                    "movimentações."
                                )
                                if len(products) == 10:  # Salvar a cada 10 produtos
                                    _flush_batch(products)
                                    products = []
                        finally:
                            if products:
                                _flush_batch(products)
                                products = []
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
                    if category_filter is None and product_limit is None:
                        site_total = sum(c["count"] or 0 for c in categories)
                        saved_total = len(load_collected_product_ids(JSON_DATA_FILE))
                        log_progress(
                            f"Comparação com o site: somatório das categorias "
                            f"{site_total}; data.json com {saved_total} produtos "
                            f"(diferença {max(site_total - saved_total, 0)})."
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
