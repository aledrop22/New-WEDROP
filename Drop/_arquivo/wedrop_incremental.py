"""Incremental WeDrop scraper: checks for changes and updates accordingly."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright

from wedrop_monitor_sistema import (
    WedropMonitor,
    BASE_URL,
    STORAGE_STATE_FILE,
    JSON_DATA_FILE,
    DB_FILE,
    configure_progress_logging,
    log_progress,
    ProductJSONLWriter,
)

from category_checker import (
    CATEGORY_COUNTS_FILE,
    get_category_counts,
    load_previous_counts,
    save_current_counts,
)


async def main() -> None:
    """Run incremental update based on category changes."""
    configure_progress_logging()
    log_progress("=" * 60)
    log_progress("INICIANDO ATUALIZAÇÃO INCREMENTAL WEDROP")
    log_progress("=" * 60)
    
    # Step 1: Check for category changes
    log_progress("\n[ETAPA 1] Verificando mudanças nas categorias...")
    previous_counts = await load_previous_counts()
    log_progress(f"Categorias anteriores: {len(previous_counts)}")
    
    async with async_playwright() as playwright:
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
                await monitor.ensure_authenticated(page, context)
                
                current_counts = await get_category_counts(page)
                log_progress(f"Categorias atuais: {len(current_counts)}")
                
                await save_current_counts(current_counts)
                
                # Detect changes
                changed_categories = []
                for cat_name, current_count in current_counts.items():
                    previous_count = previous_counts.get(cat_name, 0)
                    if current_count != previous_count:
                        changed_categories.append({
                            "name": cat_name,
                            "previous": previous_count,
                            "current": current_count,
                            "difference": current_count - previous_count,
                        })
                        log_progress(
                            f"  MUDANCA: {cat_name}: {previous_count} para {current_count} "
                            f"(diferenca: {current_count - previous_count:+d})"
                        )
                
                if not changed_categories:
                    log_progress("\n[ETAPA 2] Nenhuma mudança nas categorias.")
                    log_progress("Atualizando apenas saldos de estoque...")
                    await browser.close()
                    
                    # Run stock corrector
                    from stock_corrector import update_stock_in_file
                    await update_stock_in_file()
                    
                    log_progress("\n" + "=" * 60)
                    log_progress("ATUALIZAÇÃO INCREMENTAL CONCLUÍDA")
                    log_progress("- Apenas saldos de estoque foram atualizados")
                    log_progress("=" * 60)
                    return
                
                log_progress(f"\n[ETAPA 2] {len(changed_categories)} categorias com mudanças.")
                log_progress("Executando scraping completo das categorias alteradas...")
                
                # Import dependencies
                from sales_reporting import (
                    SalesRepository,
                    SupabaseRepository,
                    load_local_environment,
                )
                
                load_local_environment()
                supabase = SupabaseRepository.from_environment()
                supabase.validate()
                log_progress("Conexão Supabase validada.")
                
                captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
                
                # Get full category info for changed categories
                all_categories = await monitor.get_categories(page)
                changed_cat_info = [
                    cat for cat in all_categories
                    if cat["name"] in {c["name"] for c in changed_categories}
                ]
                
                log_progress(f"Categorias para rescraping: {len(changed_cat_info)}")
                
                # Clear and rebuild data.json for changed categories
                # First, load existing products
                existing_products = []
                with JSON_DATA_FILE.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                existing_products.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                
                # Remove products from changed categories
                changed_cat_names = {cat["name"] for cat in changed_cat_info}
                kept_products = [
                    p for p in existing_products
                    if p.get("category") not in changed_cat_names
                ]
                
                log_progress(
                    f"Removendo produtos de categorias alteradas: "
                    f"{len(existing_products) - len(kept_products)} produtos removidos"
                )
                
                # Rewrite kept products
                json_writer = ProductJSONLWriter(JSON_DATA_FILE)
                json_writer.start()
                for product in kept_products:
                    json_writer.append_batch([product], captured_at)
                
                log_progress(f"Produtos mantidos: {len(kept_products)}")
                
                # Scrape changed categories
                total_new_products = 0
                for category in changed_cat_info:
                    log_progress(
                        f"\n[{changed_cat_info.index(category) + 1}/{len(changed_cat_info)}] "
                        f"Scraping categoria {category['name']}..."
                    )
                    
                    product_links = await monitor.get_products_from_category(page, category)
                    log_progress(
                        f"  {len(product_links)} produtos encontrados na categoria."
                    )
                    
                    products = []
                    for product_index, (product_id, product_url) in enumerate(
                        product_links.items(), 1
                    ):
                        log_progress(
                            f"  [{product_index}/{len(product_links)}] "
                            f"Lendo produto {product_id}..."
                        )
                        try:
                            product = await monitor.get_product_details_and_history(
                                page, product_id, product_url, category["name"]
                            )
                            products.append(product)
                            
                            if len(products) == 50:
                                log_progress("  Salvando lote de 50 produtos...")
                                monitor.repository.save_products(products, captured_at)
                                json_writer.append_batch(products, captured_at)
                                supabase.save_products(products, captured_at)
                                total_new_products += len(products)
                                products = []
                        except Exception as e:
                            log_progress(f"  ERRO ao ler produto {product_id}: {e}")
                            continue
                    
                    if products:
                        log_progress(f"  Salvando lote final de {len(products)} produtos...")
                        monitor.repository.save_products(products, captured_at)
                        json_writer.append_batch(products, captured_at)
                        supabase.save_products(products, captured_at)
                        total_new_products += len(products)
                    
                    log_progress(f"  Categoria {category['name']} concluída.")
                
                supabase.close()
                
                log_progress("\n" + "=" * 60)
                log_progress("ATUALIZAÇÃO INCREMENTAL CONCLUÍDA")
                log_progress(f"- Categorias alteradas: {len(changed_categories)}")
                log_progress(f"- Produtos rescrapados: {total_new_products}")
                log_progress(f"- Produtos mantidos: {len(kept_products)}")
                log_progress("=" * 60)
                
            finally:
                await context.close()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
