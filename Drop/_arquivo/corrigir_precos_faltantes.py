"""Re-scrape SOMENTE os produtos sem preço no data.json e atualiza Supabase.

Este script:
1. Lê o data.json e identifica produtos com preço vazio.
2. Cria um backup do data.json antes de qualquer alteração.
3. Re-scrapeia APENAS os produtos sem preço (não toca nos que já têm preço).
4. Atualiza os registros no data.json in-place (preserva os demais campos).
5. Envia os produtos corrigidos para o Supabase.

Se a sessão do WeDrop expirar, reautentica e continua. Se algo falhar, o
progresso já corrigido é gravado antes de sair; ao rodar de novo, só os
produtos que continuam sem preço são lidos.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from wedrop_monitor_sistema import (
    JSON_DATA_FILE,
    STORAGE_STATE_FILE,
    WedropMonitor,
    backup_data_file,
    configure_progress_logging,
    load_local_environment,
    log_progress,
)
from sales_reporting import SupabaseRepository

# Grava o data.json e envia ao Supabase a cada N preços corrigidos.
SAVE_EVERY = 10


def load_items(json_path: Path) -> list[dict | str]:
    """Carrega o data.json linha a linha.

    Linhas que não são JSON válido são mantidas como texto, para que nada
    seja removido ao gravar de volta.
    """
    items: list[dict | str] = []
    if not json_path.is_file():
        return items
    with json_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                items.append(json.loads(stripped))
            except json.JSONDecodeError:
                items.append(stripped)
    return items


def save_items(json_path: Path, items: list[dict | str]) -> None:
    """Regrava o data.json de forma atômica (arquivo temporário + troca)."""
    tmp_path = json_path.with_name(json_path.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            line = item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
            handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, json_path)


def is_session_expired(exc: BaseException) -> bool:
    text = str(exc).casefold()
    return "sessão wedrop expirou" in text or "sessao wedrop expirou" in text


async def read_product(monitor, page, context, product: dict) -> dict:
    """Lê o produto no site, reautenticando se a sessão tiver expirado.

    Se a primeira leitura vier sem preço, espera um pouco e lê de novo.
    """
    product_id = str(product.get("product_id"))
    product_url = product.get("url") or f"https://dash.wedrop.com.br/catalog/{product_id}"
    category_name = product.get("category", "")

    async def scrape() -> dict:
        return await monitor.get_product_details_and_history(
            page, product_id, product_url, category_name
        )

    try:
        refreshed = await scrape()
    except RuntimeError as exc:
        if not is_session_expired(exc):
            raise
        log_progress("  Sessão WeDrop expirou; reautenticando...")
        await monitor.ensure_authenticated(page, context)
        log_progress("  Sessão reestabelecida; repetindo o produto.")
        refreshed = await scrape()

    if not (refreshed.get("price") or "").strip():
        await page.wait_for_timeout(3000)
        refreshed = await scrape()
    return refreshed


async def fix_missing_prices(local_only: bool = False) -> None:
    configure_progress_logging()
    log_progress("=" * 70)
    log_progress("INICIANDO CORREÇÃO DE PREÇOS FALTANTES")
    log_progress("=" * 70)

    # 1. Carregar produtos existentes e identificar os que não têm preço
    items = load_items(JSON_DATA_FILE)
    products = [item for item in items if isinstance(item, dict)]
    log_progress(f"Total de produtos no data.json: {len(products)}")

    missing_price = [
        product for product in products if not (product.get("price") or "").strip()
    ]
    log_progress(f"Produtos sem preço: {len(missing_price)}")
    if missing_price:
        ids = ", ".join(str(product.get("product_id")) for product in missing_price)
        log_progress(f"IDs sem preço: {ids}")

    if not missing_price:
        log_progress("Nenhum produto sem preço encontrado. Nada a fazer.")
        return

    # 2. Backup do data.json ANTES de qualquer alteração
    backup_data_file(JSON_DATA_FILE)

    # 3. Preparar Supabase
    load_local_environment()
    supabase = None
    if not local_only:
        supabase = SupabaseRepository.from_environment()
        supabase.validate()
        log_progress("Conexão Supabase validada.")
    else:
        log_progress("Modo local: Supabase não será atualizado.")

    captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
    by_id = {str(product.get("product_id")): product for product in products}
    pending_ids: list[str] = []  # corrigidos localmente, ainda não enviados
    fixed_count = 0
    still_missing: list[str] = []

    def flush() -> None:
        """Grava o data.json e envia ao Supabase os corrigidos pendentes."""
        nonlocal pending_ids
        if pending_ids:
            save_items(JSON_DATA_FILE, items)
            log_progress(f"  data.json gravado ({fixed_count} corrigidos até agora).")
        if supabase is not None and pending_ids:
            batch = [by_id[product_id] for product_id in pending_ids]
            log_progress(f"Enviando {len(batch)} produtos corrigidos para o Supabase...")
            supabase.save_products(batch, captured_at)
            log_progress("Produtos corrigidos enviados ao Supabase.")
            pending_ids = []

    # 4. Re-scrapear apenas os produtos sem preço
    monitor = WedropMonitor()
    try:
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
                    await monitor.ensure_authenticated(page, context)
                    log_progress("Sessão autenticada.")

                    for idx, product in enumerate(missing_price, 1):
                        product_id = str(product.get("product_id"))
                        log_progress(
                            f"[{idx}/{len(missing_price)}] Re-scrapeando produto "
                            f"{product_id} ({product.get('category', '')})..."
                        )
                        try:
                            refreshed = await read_product(
                                monitor, page, context, product
                            )
                        except Exception as exc:
                            if is_session_expired(exc):
                                # Sessão não se recuperou: para aqui, mantendo o progresso.
                                raise
                            log_progress(f"  ERRO ao re-scrapear {product_id}: {exc}")
                            still_missing.append(product_id)
                            continue

                        new_price = (refreshed.get("price") or "").strip()
                        if not new_price:
                            log_progress(f"  ⚠ Ainda sem preço após re-scrape: {product_id}")
                            still_missing.append(product_id)
                            continue

                        # Atualiza IN-PLACE: só os campos re-obtidos mudam.
                        product["price"] = new_price
                        new_name = (refreshed.get("name") or "").strip()
                        if (
                            new_name
                            and len(new_name) >= 3
                            and not new_name.casefold().startswith("produto ")
                            and new_name.casefold() != "resumo geral"
                        ):
                            product["name"] = new_name
                            product["title"] = new_name
                        new_avail = (refreshed.get("availability") or "").strip()
                        if new_avail and not (product.get("availability") or "").strip():
                            product["availability"] = new_avail
                        product["scrape_time"] = captured_at
                        fixed_count += 1
                        pending_ids.append(product_id)
                        log_progress(
                            f"  ✓ Preço corrigido: {new_price} "
                            f"(nome: {product.get('name', '')[:50]})"
                        )

                        if len(pending_ids) >= SAVE_EVERY:
                            flush()
                finally:
                    await context.close()
            finally:
                await browser.close()
    finally:
        # Mesmo se a execução parar no meio, o que já foi corrigido é salvo.
        flush()
        if supabase is not None:
            supabase.close()
        monitor.close()

    if still_missing:
        log_progress(
            f"⚠ {len(still_missing)} produtos ainda sem preço após re-scrape: "
            f"{still_missing[:20]}"
        )
    log_progress("=" * 70)
    log_progress(
        f"CONCLUÍDO: {fixed_count}/{len(missing_price)} preços corrigidos com sucesso."
    )
    log_progress("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Corrige apenas os produtos sem preço no data.json."
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Apenas atualiza o data.json local, sem enviar ao Supabase.",
    )
    args = parser.parse_args()

    try:
        asyncio.run(fix_missing_prices(local_only=args.local_only))
    except KeyboardInterrupt:
        log_progress("Interrompido pelo usuário. Progresso já gravado no data.json.")
        sys.exit(130)
    except Exception as exc:
        log_progress(f"Correção interrompida: {exc}. Progresso já gravado; execute de novo para continuar.")
        sys.exit(1)


if __name__ == "__main__":
    main()
