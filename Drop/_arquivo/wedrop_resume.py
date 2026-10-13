"""Resume WeDrop catalog collection from where it stopped."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright

from wedrop_monitor_sistema import (
    WedropMonitor,
    BASE_URL,
    STORAGE_STATE_FILE,
    JSON_DATA_FILE,
    configure_progress_logging,
    log_progress,
    ProductJSONLWriter,
)


async def load_collected_product_ids(json_path: Path) -> set[str]:
    """Load all product IDs already collected in data.json."""
    collected_ids = set()
    if not json_path.exists():
        return collected_ids
    
    with json_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    product = json.loads(line)
                    if "product_id" in product:
                        collected_ids.add(product["product_id"])
                except json.JSONDecodeError:
                    continue
    return collected_ids


async def resume_collection(
    email: str | None = None,
    password: str | None = None,
    prompt_for_credentials: bool = True,
    category_filter: str | None = None,
    product_limit: int | None = None,
    local_only: bool = False,
) -> None:
    """Resume collection from where it stopped."""
    configure_progress_logging()
    log_progress("Iniciando retomada da coleta do catálogo WeDrop.")
    log_progress(f"Destino JSON: {JSON_DATA_FILE}")
    
    # Load already collected product IDs
    collected_ids = await load_collected_product_ids(JSON_DATA_FILE)
    log_progress(f"Produtos já coletados: {len(collected_ids)}")
    
    from sales_reporting import (
        SalesRepository,
        SupabaseRepository,
        load_local_environment,
    )
    
    load_local_environment()
    supabase = None if local_only else SupabaseRepository.from_environment()
    if supabase is not None:
        log_progress("Validando conexão e tabelas do Supabase.")
        supabase.validate()
        log_progress("Conexão e tabelas Supabase validadas.")
    else:
        log_progress("Modo local: Supabase não será atualizado.")
    
    captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
    
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
                monitor = WedropMonitor()
                await monitor.ensure_authenticated(
                    page, context, email, password, prompt_for_credentials
                )
                log_progress("Sessão autenticada e catálogo aberto.")
                monitor = WedropMonitor()
                categories = monitor._filter_categories(
                    await monitor.get_categories(page), category_filter
                )
                log_progress(f"Categorias selecionadas: {len(categories)}.")
                
                json_writer = ProductJSONLWriter(JSON_DATA_FILE)
                # Don't clear the file - we're appending
                total_products = 0
                remaining_limit = product_limit
                
                for category_index, category in enumerate(categories, 1):
                    log_progress(
                        f"[{category_index}/{len(categories)}] "
                        f"Lendo listagem da categoria {category['name']}..."
                    )
                    product_links = await monitor.get_products_from_category(page, category)
                    
                    # Filter out already collected products
                    remaining_links = {
                        pid: url for pid, url in product_links.items()
                        if pid not in collected_ids
                    }
                    
                    skipped_count = len(product_links) - len(remaining_links)
                    if skipped_count > 0:
                        log_progress(
                            f"  {skipped_count} produtos já coletados, "
                            f"restam {len(remaining_links)}."
                        )
                    
                    if not remaining_links:
                        log_progress(f"  Categoria {category['name']} já completa.")
                        continue
                    
                    log_progress(
                        f"  Coletando {len(remaining_links)} produtos restantes "
                        f"da categoria {category['name']}."
                    )
                    
                    if remaining_limit is not None:
                        remaining_links = dict(
                            list(remaining_links.items())[:remaining_limit]
                        )
                        remaining_limit -= len(remaining_links)
                        log_progress(
                            f"  Limite aplicado: serão detalhados "
                            f"{len(remaining_links)} produtos nesta categoria."
                        )
                    
                    products = []
                    for product_index, (product_id, product_url) in enumerate(
                        remaining_links.items(), 1
                    ):
                        log_progress(
                            f"  Lendo produto {product_index}/{len(remaining_links)} "
                            f"(ID {product_id})."
                        )
                        try:
                            product = await monitor.get_product_details_and_history(
                                page, product_id, product_url, category["name"]
                            )
                            products.append(product)
                            log_progress(
                                f"  Produto lido: {product.get('name') or 'nome indisponível'}; "
                                f"histórico: {len(product.get('stock_history', []))} "
                                "movimentações."
                            )
                            
                            if len(products) == 50:
                                log_progress("  Salvando lote de 50 produtos no SQLite.")
                                monitor.repository.save_products(products, captured_at)
                                log_progress(
                                    "  Lote de 50 produtos salvo no SQLite, incluindo "
                                    "históricos de estoque."
                                )
                                json_writer.append_batch(products, captured_at)
                                log_progress("  Lote de 50 produtos gravado em data.json.")
                                if supabase is not None:
                                    log_progress(
                                        "  Enviando lote de 50 produtos e históricos "
                                        "para o Supabase."
                                    )
                                    supabase.save_products(products, captured_at)
                                    log_progress(
                                        "  Lote de 50 produtos e históricos confirmado "
                                        "no Supabase."
                                    )
                                total_products += len(products)
                                products = []
                        except Exception as e:
                            log_progress(f"  ERRO ao ler produto {product_id}: {e}")
                            continue
                    
                    if products:
                        log_progress(
                            f"  Salvando lote final de {len(products)} produtos "
                            "no SQLite."
                        )
                        monitor.repository.save_products(products, captured_at)
                        log_progress(
                            f"  Lote final de {len(products)} produtos salvo no "
                            "SQLite, incluindo históricos de estoque."
                        )
                        json_writer.append_batch(products, captured_at)
                        log_progress(
                            f"  Lote final de {len(products)} produtos gravado "
                            "em data.json."
                        )
                        if supabase is not None:
                            log_progress(
                                f"  Enviando lote final de {len(products)} produtos "
                                "e históricos para o Supabase."
                            )
                            supabase.save_products(products, captured_at)
                            log_progress(
                                f"  Lote final de {len(products)} produtos e "
                                "históricos confirmado no Supabase."
                            )
                        total_products += len(products)
                    
                    log_progress(
                        f"  Categoria concluída: {len(remaining_links)} produtos "
                        "detalhados e salvos."
                    )
                    
                    if remaining_limit == 0:
                        break
                
                destination = "localmente" if local_only else "e sincronizado"
                log_progress(
                    f"Retomada concluída {destination}: {len(categories)} "
                    f"categorias, {total_products} produtos novos."
                )
                log_progress(f"Catálogo JSON Lines: {JSON_DATA_FILE}")
                if supabase is not None:
                    log_progress(
                        "Destino remoto: Supabase (categorias, produtos e eventos)."
                    )
            finally:
                await context.close()
        finally:
            if supabase is not None:
                supabase.close()
            await browser.close()


async def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Retoma a coleta do catálogo WeDrop de onde parou."
    )
    parser.add_argument(
        "--category",
        help="Coleta apenas categorias cujo nome contenha este texto.",
    )
    parser.add_argument(
        "--limit",
        type=int,
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
            await resume_collection(
                category_filter=args.category,
                product_limit=args.limit,
                local_only=args.local_only,
            )
        except Exception:
            if logging.getLogger("wedrop.scraper").handlers:
                logging.getLogger("wedrop.scraper").exception("Retomada encerrada com erro.")
            raise
    finally:
        monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
