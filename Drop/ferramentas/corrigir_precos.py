"""Preenche o preço dos produtos que estão sem preço no data.json.

Só lê os produtos sem preço; os demais não são tocados. Faz backup antes,
grava em pontos de controle e envia ao Supabase o que foi corrigido.
Se a sessão cair, reautentica. Se parar, o que já foi corrigido fica salvo,
e a próxima execução só relê os que continuam sem preço.

Uso: python -m ferramentas.corrigir_precos [--local]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime

from playwright.async_api import async_playwright

from wedrop.config import BATCH_SIZE, load_environment
from wedrop.logs import configure_progress_logging, log_progress
from wedrop.mapping import DataPaths
from wedrop.scraping.browser import open_browser
from wedrop.scraping.product_page import ProductJob, ProductReader
from wedrop.scraping.session import SessionExpiredError, ensure_authenticated
from wedrop.storage import products_file
from wedrop.storage.supabase_repository import SupabaseRepository

PRODUCT_URL = "https://dash.wedrop.com.br/catalog/{product_id}"


def _has_price(product: dict) -> bool:
    return bool((product.get("price") or "").strip())


def _usable_name(name: str) -> bool:
    cleaned = name.strip()
    return len(cleaned) >= 3 and not cleaned.casefold().startswith("produto ") and cleaned.casefold() != "resumo geral"


def _apply_refresh(product: dict, refreshed: dict, captured_at: str) -> None:
    """Atualiza só os campos que estavam vazios ou faltando; o resto permanece igual."""
    product["price"] = refreshed["price"].strip()
    name = (refreshed.get("name") or "").strip()
    if _usable_name(name):
        product["name"] = name
        product["title"] = name
    availability = (refreshed.get("availability") or "").strip()
    if availability and not (product.get("availability") or "").strip():
        product["availability"] = availability
    product["scrape_time"] = captured_at


async def _read_with_reauth(reader: ProductReader, page, context, job: ProductJob) -> dict:
    try:
        refreshed = await reader.read(job)
    except SessionExpiredError:
        log_progress("  Sessão WeDrop expirou; reautenticando...")
        await ensure_authenticated(page, context, ask_user=False)
        refreshed = await reader.read(job)
    if not _has_price(refreshed):
        # Página que ainda não terminou de carregar: uma segunda leitura costuma resolver.
        await page.wait_for_timeout(3000)
        refreshed = await reader.read(job)
    return refreshed


async def fix_missing_prices(paths: DataPaths, local_only: bool) -> int:
    load_environment()
    configure_progress_logging()
    records = products_file.read_records(paths.products_file)
    products = {str(record["product_id"]): record for record in records if isinstance(record, dict)}
    missing = [product for product in products.values() if not _has_price(product)]
    log_progress(f"Produtos no data.json: {len(products)}; sem preço: {len(missing)}.")
    if not missing:
        return 0

    backup = products_file.backup_products_file(paths.products_file, paths.backup_dir)
    if backup is not None:
        log_progress(f"Backup de segurança criado: {backup.name}")

    supabase = None
    if not local_only:
        supabase = SupabaseRepository.from_environment()
        supabase.validate()
    captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
    pending_ids: list[str] = []
    fixed = 0

    def checkpoint() -> None:
        """Grava o data.json e envia ao Supabase os corrigidos desde o último ponto de controle."""
        if not pending_ids:
            return
        products_file.write_records_atomic(paths.products_file, records)
        if supabase is not None:
            supabase.save_products([products[product_id] for product_id in pending_ids], captured_at)
        log_progress(f"  Ponto de controle: {fixed} corrigidos até agora.")
        pending_ids.clear()

    try:
        async with async_playwright() as playwright:
            browser, context = await open_browser(playwright)
            try:
                page = await context.new_page()
                await ensure_authenticated(page, context, ask_user=False)
                reader = ProductReader(page)
                for index, product in enumerate(missing, 1):
                    product_id = str(product["product_id"])
                    job = ProductJob(
                        product_id,
                        product.get("url") or PRODUCT_URL.format(product_id=product_id),
                        product.get("category", ""),
                    )
                    log_progress(f"[{index}/{len(missing)}] Relendo produto {product_id} ({job.category_name})...")
                    try:
                        refreshed = await _read_with_reauth(reader, page, context, job)
                    except SessionExpiredError:
                        raise  # a sessão não se recuperou: para e mantém o progresso
                    except Exception as exc:
                        log_progress(f"  ERRO ao reler {product_id}: {exc}")
                        continue
                    if not _has_price(refreshed):
                        log_progress(f"  ⚠ Continua sem preço no site: {product_id}")
                        continue
                    _apply_refresh(product, refreshed, captured_at)
                    pending_ids.append(product_id)
                    fixed += 1
                    log_progress(f"  ✓ Preço: {product['price']} ({product.get('name', '')[:50]})")
                    if len(pending_ids) >= BATCH_SIZE:
                        checkpoint()
            finally:
                await browser.close()
    finally:
        checkpoint()
        if supabase is not None:
            supabase.close()

    log_progress(f"CONCLUÍDO: {fixed}/{len(missing)} preços corrigidos.")
    return fixed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preenche preços faltantes no data.json.")
    parser.add_argument("--local", action="store_true", help="Não envia ao Supabase.")
    args = parser.parse_args(argv)
    try:
        asyncio.run(fix_missing_prices(DataPaths(), local_only=args.local))
    except KeyboardInterrupt:
        log_progress("Interrompido. O progresso já gravado foi preservado.")
        return 130
    except Exception as exc:
        log_progress(f"Correção encerrada com erro: {type(exc).__name__}: {exc}. Execute de novo para continuar.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
