"""Quick category count checker to detect changes."""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

from wedrop_monitor_sistema import (
    BASE_URL,
    STORAGE_STATE_FILE,
    WedropMonitor,
    configure_progress_logging,
    log_progress,
)

CATEGORY_COUNTS_FILE = Path(__file__).parent / "category_counts.json"


async def get_category_counts(page) -> dict[str, int]:
    """Get current product counts for all categories."""
    monitor = WedropMonitor()
    categories = await monitor.get_categories(page)
    return {cat["name"]: cat["count"] or 0 for cat in categories}


async def load_previous_counts() -> dict[str, int]:
    """Load previously saved category counts."""
    if not CATEGORY_COUNTS_FILE.exists():
        return {}
    with CATEGORY_COUNTS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


async def save_current_counts(counts: dict[str, int]) -> None:
    """Save current category counts."""
    with CATEGORY_COUNTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(counts, f, ensure_ascii=False, indent=2)


async def detect_changes() -> dict[str, dict]:
    """Detect which categories have changed."""
    configure_progress_logging()
    log_progress("Verificando mudanças nas categorias...")
    
    previous_counts = await load_previous_counts()
    log_progress(f"Categorias anteriormente registradas: {len(previous_counts)}")
    
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
                log_progress("Contagens atuais salvas.")
                
                changes = {}
                for cat_name, current_count in current_counts.items():
                    previous_count = previous_counts.get(cat_name, 0)
                    if current_count != previous_count:
                        changes[cat_name] = {
                            "previous": previous_count,
                            "current": current_count,
                            "difference": current_count - previous_count,
                        }
                        log_progress(
                            f"  {cat_name}: {previous_count} para {current_count} "
                            f"(diferenca: {current_count - previous_count:+d})"
                        )
                
                if not changes:
                    log_progress("Nenhuma mudança detectada nas categorias.")
                else:
                    log_progress(f"{len(changes)} categorias com mudanças detectadas.")
                
                return changes
            finally:
                await context.close()
        finally:
            await browser.close()


async def main() -> None:
    changes = await detect_changes()
    print(json.dumps(changes, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
