"""Coleta completa do catálogo: categorias, listagens, produtos e gravação.

Regras de execução:
- Sempre cria um backup do data.json antes de tocar nele.
- Coleta concluída anteriormente: começa do zero (o data.json é reescrito).
- Coleta interrompida (erro ou queda): retoma sem apagar nada, sem repetir o
  que já está salvo, e completa o que faltou em relação ao site.
- Coleta parcial (--categoria ou --limite): só acrescenta dados e não altera o estado.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.async_api import BrowserContext, Page, async_playwright

from .config import (
    BACKUP_DIR,
    BATCH_SIZE,
    DATABASE_FILE,
    DEFAULT_WORKERS,
    PRODUCTS_FILE,
    RUN_STATE_FILE,
    load_environment,
)
from .logs import configure_progress_logging, log_progress
from .scraping.browser import open_browser
from .scraping.catalog import Category, filter_categories, list_categories, read_category_links
from .scraping.product_page import ProductJob, ProductReader
from .scraping.session import SessionExpiredError, ensure_authenticated
from .storage import products_file
from .storage.run_state import COMPLETED, IN_PROGRESS, load_run_state, save_run_state
from .storage.sqlite_repository import SalesRepository
from .storage.supabase_repository import SupabaseRepository

MAX_RELOGINS_PER_CRAWL = 3


@dataclass(frozen=True)
class DataPaths:
    """Onde ficam os arquivos da coleta. Pode ser trocado para testes em pasta temporária."""

    products_file: Path = PRODUCTS_FILE
    backup_dir: Path = BACKUP_DIR
    state_file: Path = RUN_STATE_FILE
    database_file: Path = DATABASE_FILE

    @classmethod
    def in_folder(cls, folder: Path) -> DataPaths:
        return cls(
            products_file=folder / "data.json",
            backup_dir=folder / "backups",
            state_file=folder / "estado_coleta.json",
            database_file=folder / "wedrop_monitoramento.db",
        )


@dataclass(frozen=True)
class MappingOptions:
    category_filter: str | None = None
    product_limit: int | None = None
    local_only: bool = False
    workers: int = DEFAULT_WORKERS
    ask_for_credentials: bool = True

    @property
    def is_partial(self) -> bool:
        return self.category_filter is not None or self.product_limit is not None


@dataclass
class MappingSummary:
    categories: int = 0
    site_total: int = 0
    saved_total: int = 0
    resumed: bool = False
    partial: bool = False
    shortfall_categories: list[str] = field(default_factory=list)
    failed_ids: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not self.partial and not self.shortfall_categories and not self.failed_ids


class _BatchSink:
    """Grava cada lote no SQLite, no data.json e no Supabase, nessa ordem."""

    def __init__(
        self,
        paths: DataPaths,
        repository: SalesRepository,
        supabase: SupabaseRepository | None,
        captured_at: str,
    ):
        self._paths = paths
        self._repository = repository
        self._supabase = supabase
        self._captured_at = captured_at
        self._batch: list[dict] = []

    def add(self, product: dict) -> None:
        self._batch.append(product)
        if len(self._batch) >= BATCH_SIZE:
            self.flush()

    def flush(self) -> None:
        if not self._batch:
            return
        batch, self._batch = self._batch, []
        self._repository.save_products(batch, self._captured_at)
        products_file.append_records(
            self._paths.products_file,
            [products_file.file_record(product, self._captured_at) for product in batch],
        )
        if self._supabase is not None:
            self._supabase.save_products(batch, self._captured_at)
        destinations = "SQLite e data.json" + ("" if self._supabase is None else " e Supabase")
        log_progress(f"Lote de {len(batch)} produtos gravado em {destinations}.")


class _ProductCrawler:
    """Lê os produtos com uma página do navegador por worker e entrega cada um ao sink."""

    def __init__(self, readers: list[ProductReader], sink: _BatchSink, relogin):
        self._readers = readers
        self._sink = sink
        self._relogin = relogin
        self._done = 0
        self._total = 0

    async def crawl(self, jobs: list[ProductJob]) -> list[tuple[ProductJob, Exception]]:
        pending: deque[ProductJob] = deque(jobs)
        self._done, self._total = 0, len(jobs)
        failures: list[tuple[ProductJob, Exception]] = []
        relogins = 0
        while pending:
            session_lost = asyncio.Event()
            await asyncio.gather(
                *(self._work(reader, pending, failures, session_lost) for reader in self._readers)
            )
            if session_lost.is_set():
                relogins += 1
                if relogins > MAX_RELOGINS_PER_CRAWL:
                    raise RuntimeError("A sessão WeDrop expirou repetidamente; a coleta foi interrompida.")
                self._sink.flush()
                log_progress("  Sessão WeDrop expirou; reautenticando e retomando de onde parou...")
                await self._relogin()
        self._sink.flush()
        return failures

    async def _work(
        self,
        reader: ProductReader,
        pending: deque[ProductJob],
        failures: list[tuple[ProductJob, Exception]],
        session_lost: asyncio.Event,
    ) -> None:
        while pending and not session_lost.is_set():
            job = pending.popleft()
            try:
                product = await reader.read(job)
            except SessionExpiredError:
                pending.appendleft(job)
                session_lost.set()
                return
            except Exception as exc:  # um produto com erro não derruba a coleta inteira
                failures.append((job, exc))
                log_progress(f"  ERRO ao ler produto {job.product_id}: {exc}")
                continue
            self._done += 1
            self._report(product)
            self._sink.add(product)

    def _report(self, product: dict) -> None:
        missing = []
        if not product.get("name") or len(product["name"]) < 3:
            missing.append("nome")
        if not product.get("price"):
            missing.append("preço")
        if not product.get("availability"):
            missing.append("disponibilidade")
        if missing:
            log_progress(f"⚠️ Campos vazios: {', '.join(missing)} (ID {product['product_id']})")
        log_progress(
            f"[{self._done}/{self._total}] {product.get('name') or 'nome indisponível'} "
            f"(ID {product['product_id']}): {len(product.get('stock_history', []))} movimentações."
        )


async def _read_listing(page: Page, category: Category, summary: MappingSummary) -> dict[str, str]:
    """Lista da categoria. Se faltar produto em relação ao site, avisa e registra a divergência."""
    links = await read_category_links(page, category)
    if category.count is not None and len(links) < category.count:
        log_progress(
            f"AVISO: o site informa {category.count} produtos em {category.name}, "
            f"mas a listagem trouxe {len(links)}."
        )
        summary.shortfall_categories.append(category.name)
    return links


def _prepare_products_file(paths: DataPaths, options: MappingOptions, state) -> bool:
    """Backup e preparação do data.json. Retorna True quando a coleta retoma uma anterior."""
    backup = products_file.backup_products_file(paths.products_file, paths.backup_dir)
    if backup is not None:
        log_progress(f"Backup de segurança criado: {backup.name}")
    products_file.compress_old_backups(paths.backup_dir)

    resuming = options.is_partial or (state is not None and state.is_in_progress)
    if not resuming:
        products_file.write_records_atomic(paths.products_file, [])
        log_progress("Coleta anterior concluída: data.json será reescrito do zero.")
    elif not options.is_partial:
        # Não restaura produtos de backups: um backup antigo traz dados de dias
        # anteriores e faria produtos parecerem coletados hoje sem nova leitura.
        log_progress("Coleta anterior incompleta: retomando sem repetir produtos já salvos.")
    return resuming


async def run_mapping(
    options: MappingOptions = MappingOptions(),
    paths: DataPaths = DataPaths(),
) -> MappingSummary:
    load_environment()
    configure_progress_logging()
    log_progress("Iniciando coleta completa do catálogo WeDrop.")
    log_progress(f"Destino JSON: {paths.products_file}")

    supabase = None
    if not options.local_only:
        supabase = SupabaseRepository.from_environment()
        supabase.validate()
        log_progress("Conexão e tabelas Supabase validadas.")

    state = None if options.is_partial else load_run_state(paths.state_file)
    resuming = _prepare_products_file(paths, options, state)
    summary = MappingSummary(resumed=resuming, partial=options.is_partial)
    if not options.is_partial:
        save_run_state(paths.state_file, IN_PROGRESS, saved_total=len(products_file.read_product_ids(paths.products_file)))

    repository = SalesRepository(paths.database_file)
    captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
    sink = _BatchSink(paths, repository, supabase, captured_at)
    try:
        async with async_playwright() as playwright:
            browser, context = await open_browser(playwright)
            try:
                await _map_catalog(context, options, paths, sink, repository, supabase, captured_at, summary)
            finally:
                await browser.close()
    finally:
        repository.close()
        if supabase is not None:
            supabase.close()

    _finish(paths, summary)
    return summary


async def _map_catalog(
    context: BrowserContext,
    options: MappingOptions,
    paths: DataPaths,
    sink: _BatchSink,
    repository: SalesRepository,
    supabase: SupabaseRepository | None,
    captured_at: str,
    summary: MappingSummary,
) -> None:
    pages = [await context.new_page() for _ in range(max(1, options.workers))]
    listing_page = pages[0]

    async def relogin() -> None:
        await ensure_authenticated(listing_page, context, ask_user=options.ask_for_credentials)

    await relogin()
    categories = filter_categories(await list_categories(listing_page), options.category_filter)
    summary.categories = len(categories)
    summary.site_total = sum(category.count or 0 for category in categories)
    log_progress(f"Categorias selecionadas: {len(categories)}; o site informa {summary.site_total} produtos.")

    saved_ids = products_file.read_product_ids(paths.products_file)
    crawler = _ProductCrawler([ProductReader(page) for page in pages], sink, relogin)
    remaining = options.product_limit
    for index, category in enumerate(categories, 1):
        log_progress(f"[{index}/{len(categories)}] Lendo listagem da categoria {category.name}...")
        links = await _read_listing(listing_page, category, summary)
        pending = [
            ProductJob(product_id, url, category.name)
            for product_id, url in links.items()
            if product_id not in saved_ids
        ]
        if remaining is not None:
            pending = pending[:remaining]
            remaining -= len(pending)

        repository.save_category(_as_dict(category), len(links), captured_at)
        if supabase is not None:
            supabase.save_category(_as_dict(category), len(links), captured_at)
        log_progress(f"Categoria {category.name}: {len(links)} listados, {len(pending)} a ler.")
        if pending:
            failures = await crawler.crawl(pending)
            summary.failed_ids.extend(job.product_id for job, _ in failures)
        if remaining == 0:
            break


def _as_dict(category: Category) -> dict:
    return {"name": category.name, "url": category.url, "count": category.count}


def _finish(paths: DataPaths, summary: MappingSummary) -> None:
    summary.saved_total = len(products_file.read_product_ids(paths.products_file))
    if not summary.partial:
        status = COMPLETED if summary.is_complete else IN_PROGRESS
        save_run_state(paths.state_file, status, summary.site_total, summary.saved_total)
    log_progress(
        f"Comparação com o site: {summary.site_total} produtos informados; "
        f"data.json com {summary.saved_total} (diferença {max(summary.site_total - summary.saved_total, 0)})."
    )
    if summary.failed_ids:
        log_progress(f"Produtos com erro, retomados na próxima execução: {summary.failed_ids[:20]}")
    log_progress("Mapeamento concluído." if summary.is_complete else "Mapeamento incompleto; execute novamente para retomar.")
