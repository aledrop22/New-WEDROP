"""Update only stock fields in existing data.json without full rescrape."""

import asyncio
import json
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from wedrop_monitor_sistema import (
    BASE_URL,
    STORAGE_STATE_FILE,
    WedropMonitor,
    configure_progress_logging,
    log_progress,
    value_for_label,
)

JSON_DATA_FILE = Path(__file__).parent / "data.json"


async def extract_stock_balance(page) -> dict[str, str]:
    """Extract stock, total_stock_count, and real_balance from product page."""
    # Click on stock/values tab
    stock_tab = page.get_by_role("tab", name=re.compile("(Valores|Estoque|Saldo)", re.I))
    if await stock_tab.count():
        await stock_tab.first.click()
        await page.wait_for_timeout(400)
    
    page_text = await page.locator("body").inner_text()
    
    stock = value_for_label(
        page_text,
        ("Estoque", "Disponibilidade", "Saldo disponível", "Estoque disponível"),
    )
    real_balance = value_for_label(page_text, ("Saldo real", "Saldo"))
    total_stock = value_for_label(page_text, ("Estoque total", "Total em estoque"))
    
    return {
        "stock": stock,
        "total_stock_count": total_stock,
        "real_balance": real_balance,
    }


async def update_product_stock(product_url: str) -> dict[str, str]:
    """Fetch stock data for a single product."""
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
                
                await page.goto(product_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(500)
                
                stock_data = await extract_stock_balance(page)
                return stock_data
            finally:
                await context.close()
        finally:
            await browser.close()


async def update_stock_in_file() -> None:
    """Update stock fields in data.json for all products."""
    configure_progress_logging()
    log_progress("Iniciando atualização de saldos no data.json.")
    
    # Read all products
    products = []
    with JSON_DATA_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    products.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    log_progress(f"Total de produtos no data.json: {len(products)}")
    
    # Update stock for each product
    updated_count = 0
    for idx, product in enumerate(products, 1):
        product_id = product.get("product_id")
        product_url = product.get("url")
        
        if not product_url:
            log_progress(f"  [{idx}/{len(products)}] Produto {product_id} sem URL, pulando.")
            continue
        
        log_progress(f"  [{idx}/{len(products)}] Atualizando estoque do produto {product_id}...")
        
        try:
            stock_data = await update_product_stock(product_url)
            
            # Update only stock fields
            product["stock"] = stock_data["stock"]
            product["total_stock_count"] = stock_data["total_stock_count"]
            product["real_balance"] = stock_data["real_balance"]
            
            updated_count += 1
            log_progress(
                f"  [{idx}/{len(products)}] Produto {product_id} atualizado: "
                f"stock={stock_data['stock']}, "
                f"total={stock_data['total_stock_count']}, "
                f"saldo={stock_data['real_balance']}"
            )
        except Exception as e:
            log_progress(f"  [{idx}/{len(products)}] ERRO ao atualizar produto {product_id}: {e}")
            continue
    
    # Write back to file
    log_progress("Gravando dados atualizados no data.json...")
    with JSON_DATA_FILE.open("w", encoding="utf-8", newline="\n") as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + "\n")
    
    log_progress(f"Atualização concluída: {updated_count}/{len(products)} produtos atualizados.")


async def main() -> None:
    await update_stock_in_file()


if __name__ == "__main__":
    asyncio.run(main())
