"""Script para corrigir nomes de produtos buscando do site WeDrop"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
from product_naming import clean_product_name
from sales_reporting import load_local_environment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "data.json"
OUTPUT_FILE = Path(__file__).parent / "data_corrigido_site.json"
STORAGE_STATE_FILE = Path(__file__).parent / "storage_state.json"
BASE_URL = "https://dash.wedrop.com.br"


async def get_product_name_from_url(page, product_url: str) -> str:
    """Busca o nome do produto diretamente do site WeDrop"""
    try:
        await page.goto(product_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        # Tentar seletores específicos do WeDrop
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
                    return candidate

        # Tentar seletores genéricos
        name_node = page.locator("h1, h2").first
        name = (await name_node.inner_text()).strip() if await name_node.count() else ""

        if name and name.casefold() not in {"produto", "product", "wedrop"}:
            return name

        # Tentar do título da página
        page_title = (await page.title()).strip()
        import re
        page_title = re.sub(r"^(?:we\s*drop|wedrop|we-drop)\s*[-–:]?\s*", "", page_title, flags=re.IGNORECASE)
        if page_title.casefold() not in {"wedrop", "produto", "product"}:
            return page_title

        return ""
    except Exception as e:
        logger.error(f"Erro ao buscar nome de {product_url}: {e}")
        return ""


async def ensure_authenticated(page, context):
    """Garante que está autenticado no WeDrop"""
    await page.goto(f"{BASE_URL}/catalog", wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)

    # Verificar se precisa de login
    if await page.locator('input[type="password"]').count():
        logger.error("Sessão expirada. Por favor, execute o scraper principal primeiro para autenticar.")
        raise RuntimeError("Sessão expirada. Execute wedrop_monitor_sistema.py para autenticar.")


async def fix_product_names():
    """Corrige nomes de produtos buscando do site"""
    load_local_environment()

    # Carregar produtos
    products = []
    with DATA_FILE.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    products.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    logger.info(f"Total de produtos: {len(products)}")

    # Identificar produtos com nomes genéricos
    products_to_fix = []
    for product in products:
        name = product.get("name", "")
        if name.startswith("Produto ") and " (" in name:
            products_to_fix.append(product)

    logger.info(f"Produtos para corrigir: {len(products_to_fix)}")

    if not products_to_fix:
        logger.info("Nenhum produto precisa de correção")
        return

    # Iniciar navegador
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)

        # Tentar usar sessão salva
        if STORAGE_STATE_FILE.exists():
            context = await browser.new_context(storage_state=str(STORAGE_STATE_FILE))
        else:
            context = await browser.new_context()

        page = await context.new_page()

        # Verificar autenticação
        try:
            await ensure_authenticated(page, context)
        except RuntimeError as e:
            await context.close()
            await browser.close()
            raise

        fixed_count = 0
        for i, product in enumerate(products_to_fix, 1):
            product_url = product.get("url", "")
            product_id = product.get("product_id", "")

            logger.info(f"[{i}/{len(products_to_fix)}] Corrigindo produto {product_id}...")

            if not product_url:
                logger.warning(f"Produto {product_id} não tem URL")
                continue

            # Buscar nome do site
            real_name = await get_product_name_from_url(page, product_url)

            if real_name:
                # Limpar o nome
                cleaned_name = clean_product_name(real_name, product.get("description", ""))
                if cleaned_name:
                    product["name"] = cleaned_name
                    fixed_count += 1
                    logger.info(f"  ✓ Nome corrigido: {cleaned_name[:50]}...")
                else:
                    logger.warning(f"  Nome encontrado mas limpeza falhou: {real_name[:50]}...")
            else:
                logger.warning(f"  Não foi possível encontrar nome para produto {product_id}")

            # Pequena pausa para não sobrecarregar
            await page.wait_for_timeout(200)

        await context.close()
        await browser.close()

    logger.info(f"Total de nomes corrigidos: {fixed_count}")

    # Salvar arquivo corrigido
    with OUTPUT_FILE.open('w', encoding='utf-8') as f:
        for product in products:
            f.write(json.dumps(product, ensure_ascii=False) + "\n")

    logger.info(f"Arquivo corrigido salvo em: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(fix_product_names())
