import asyncio
import datetime
import logging
import os
import re
import sys

import scrapy
from itemloaders.processors import MapCompose, TakeFirst
from parsel import Selector
from scrapy.loader import ItemLoader
from scrapy_playwright.page import PageMethod

# WORKAROUND para Windows: Forçar ProactorEventLoop para Playwright funcionar com subprocessos
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception as e:
        print(f"Aviso: Não foi possível definir ProactorEventLoopPolicy: {e}")

SITE_HOST = "dash.wedrop.com.br"
STORAGE_STATE_FILE = 'storage_state.json'


def clean_text(text):
    if text:
        return text.strip()
    return None


class WedropCatalogSpider(scrapy.Spider):
    name = "wedrop_catalog"
    allowed_domains = [SITE_HOST]
    start_urls = [f"https://{SITE_HOST}/catalog"]

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(WedropCatalogSpider, cls).from_crawler(crawler, *args, **kwargs)

        if not os.path.exists(STORAGE_STATE_FILE):
            raise ValueError(f"!!! ERRO: Ficheiro '{STORAGE_STATE_FILE}' não encontrado! Execute o 'obter_cookie_novo_site.py' primeiro. !!!")

        spider.storage_state = STORAGE_STATE_FILE
        spider.log(f"Storage state carregado de '{STORAGE_STATE_FILE}'. Cookies e localStorage incluídos.")

        spider.categories_found = []
        spider.page_count = 0
        return spider

    def start_requests(self):
        url = self.start_urls[0]
        timestamp = int(__import__('time').time() * 1000)
        cache_busted_url = f"{url}?cache_buster={timestamp}"
        self.log(f"Usando URL com Cache Buster: {cache_busted_url}")

        yield scrapy.Request(
            cache_busted_url,
            callback=self.parse_catalog,
            dont_filter=True,
            meta=dict(
                playwright=True,
                playwright_stealth=True,
                playwright_include_page=True,
                playwright_context_kwargs={'storage_state': self.storage_state},
                playwright_page_goto_kwargs=dict(
                    wait_until="domcontentloaded",
                    timeout=45000
                ),
                playwright_page_methods=[
                    PageMethod("wait_for_selector", "div[class*='category'], div[class*='Category']", timeout=15000)
                ]
            )
        )

    async def parse_catalog(self, response):
        try:
            self.page_count += 1
            self.log(f"\n{'='*80}")
            self.log(f"[PÁGINA CATALOGO]: {response.url}")

            page = response.meta["playwright_page"]

            try:
                await page.wait_for_timeout(2000)
            except:
                pass

            try:
                page_content = await asyncio.wait_for(page.content(), timeout=10.0)
            except asyncio.TimeoutError:
                self.log(f"ERRO: Timeout ao obter conteúdo do catálogo. Usando fallback.")
                try:
                    page_content = await page.evaluate("() => document.documentElement.outerHTML")
                except:
                    try:
                        await page.close()
                    except:
                        pass
                    return
            except Exception as e:
                self.log(f"ERRO ao obter conteúdo do catálogo: {e}")
                try:
                    page_content = await page.evaluate("() => document.documentElement.outerHTML")
                except:
                    try:
                        await page.close()
                    except:
                        pass
                    return

            selector = Selector(text=page_content)

            from Site.items import WedropCategoryItem

            now = datetime.datetime.now()
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

            # Try to extract categories - multiple selectors based on possible HTML structures
            category_selectors = [
                'div[class*="category"]',
                'div[class*="Category"]',
                'div[role="button"]',
                'button[class*="category"]',
                'a[href*="/catalog/"]',
            ]

            categories_found = []
            for cat_selector in category_selectors:
                category_elements = selector.css(cat_selector)
                if category_elements:
                    self.log(f"Encontrados {len(category_elements)} elementos com seletor: {cat_selector}")
                    for idx, elem in enumerate(category_elements[:50]):  # Limit to first 50
                        text = elem.css('::text').getall()
                        text_content = " ".join([t.strip() for t in text if t.strip()])
                        
                        href = elem.css('::attr(href)').get()
                        
                        # Try to extract count from text
                        count_match = re.search(r'(\d+)', text_content)
                        count = count_match.group(1) if count_match else None
                        
                        if text_content and (href or count):
                            category_item = WedropCategoryItem()
                            category_item['category_name'] = text_content
                            category_item['category_count'] = count or '0'
                            category_item['category_url'] = href or ''
                            category_item['scrape_time'] = timestamp_str
                            categories_found.append(category_item)
                            self.log(f"Categoria encontrada: {text_content} (Count: {count}, URL: {href})")
                    
                    if categories_found:
                        break

            if not categories_found:
                self.log("Nenhuma categoria encontrada com seletores padrão. Tentando extração genérica...")
                # Generic extraction - look for any elements with numbers
                all_divs = selector.css('div')
                for div in all_divs[:100]:
                    text = div.css('::text').getall()
                    text_content = " ".join([t.strip() for t in text if t.strip()])
                    if text_content and re.search(r'[A-Za-z]{3,}', text_content) and re.search(r'\d+', text_content):
                        self.log(f"Elemento potencial de categoria: {text_content}")

            for cat in categories_found:
                yield cat

            # If categories have URLs, navigate to them
            for cat in categories_found:
                cat_url = cat.get('category_url')
                if cat_url and cat_url.startswith('/'):
                    full_url = f"https://{SITE_HOST}{cat_url}"
                    self.log(f"Navegando para categoria: {cat.get('category_name')} - {full_url}")
                    yield scrapy.Request(
                        full_url,
                        callback=self.parse_category,
                        dont_filter=True,
                        meta=dict(
                            playwright=True,
                            playwright_stealth=True,
                            playwright_include_page=True,
                            playwright_context_kwargs={'storage_state': self.storage_state},
                            playwright_page_goto_kwargs=dict(
                                wait_until="domcontentloaded",
                                timeout=45000
                            ),
                            category_name=cat.get('category_name')
                        )
                    )

            try:
                await page.close()
            except:
                pass

        except Exception as parse_error:
            self.log(f"❌ ERRO CRÍTICO no parse_catalog(): {parse_error}", level=logging.ERROR)
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", level=logging.ERROR)
            try:
                page = response.meta.get("playwright_page")
                if page:
                    await page.close()
            except:
                pass

    async def parse_category(self, response):
        try:
            category_name = response.meta.get('category_name', 'Unknown')
            self.log(f"\n{'='*80}")
            self.log(f"[CATEGORIA]: {category_name} - {response.url}")

            page = response.meta["playwright_page"]

            try:
                await page.wait_for_timeout(2000)
            except:
                pass

            try:
                page_content = await asyncio.wait_for(page.content(), timeout=10.0)
            except asyncio.TimeoutError:
                self.log(f"ERRO: Timeout ao obter conteúdo da categoria. Usando fallback.")
                try:
                    page_content = await page.evaluate("() => document.documentElement.outerHTML")
                except:
                    try:
                        await page.close()
                    except:
                        pass
                    return
            except Exception as e:
                self.log(f"ERRO ao obter conteúdo da categoria: {e}")
                try:
                    page_content = await page.evaluate("() => document.documentElement.outerHTML")
                except:
                    try:
                        await page.close()
                    except:
                        pass
                    return

            selector = Selector(text=page_content)

            # Look for product links or cards
            product_selectors = [
                'a[href*="/catalog/"]',
                'div[class*="product"]',
                'div[class*="Product"]',
            ]

            product_links = []
            for prod_selector in product_selectors:
                links = selector.css(prod_selector)
                if links:
                    for link in links:
                        href = link.css('::attr(href)').get()
                        if href and '/catalog/' in href:
                            if href not in product_links:
                                product_links.append(href)
                    if product_links:
                        break

            self.log(f"Encontrados {len(product_links)} produtos na categoria {category_name}")

            for product_url in product_links:
                if product_url.startswith('/'):
                    full_url = f"https://{SITE_HOST}{product_url}"
                else:
                    full_url = product_url
                
                self.log(f"Processando produto: {full_url}")
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_product,
                    dont_filter=True,
                    meta=dict(
                        playwright=True,
                        playwright_stealth=True,
                        playwright_include_page=True,
                        playwright_context_kwargs={'storage_state': self.storage_state},
                        playwright_page_goto_kwargs=dict(
                            wait_until="domcontentloaded",
                            timeout=45000
                        ),
                        category_name=category_name
                    )
                )

            try:
                await page.close()
            except:
                pass

        except Exception as parse_error:
            self.log(f"❌ ERRO CRÍTICO no parse_category(): {parse_error}", level=logging.ERROR)
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", level=logging.ERROR)
            try:
                page = response.meta.get("playwright_page")
                if page:
                    await page.close()
            except:
                pass

    async def parse_product(self, response):
        try:
            category_name = response.meta.get('category_name', 'Unknown')
            self.log(f"Extraindo dados do produto: {response.url}")

            page = response.meta["playwright_page"]

            try:
                await page.wait_for_timeout(2000)
            except:
                pass

            # Try to click on "Histórico de Estoque" tab if it exists
            try:
                stock_history_tab = page.locator('text=Histórico de Estoque')
                if await stock_history_tab.count() > 0:
                    await stock_history_tab.first.click()
                    await page.wait_for_timeout(1000)
                    self.log("Clicou na aba Histórico de Estoque")
            except Exception as e:
                self.log(f"Não foi possível clicar na aba de histórico: {e}")

            try:
                page_content = await asyncio.wait_for(page.content(), timeout=10.0)
            except asyncio.TimeoutError:
                self.log(f"ERRO: Timeout ao obter conteúdo do produto. Usando fallback.")
                try:
                    page_content = await page.evaluate("() => document.documentElement.outerHTML")
                except:
                    try:
                        await page.close()
                    except:
                        pass
                    return
            except Exception as e:
                self.log(f"ERRO ao obter conteúdo do produto: {e}")
                try:
                    page_content = await page.evaluate("() => document.documentElement.outerHTML")
                except:
                    try:
                        await page.close()
                    except:
                        pass
                    return

            selector = Selector(text=page_content)

            from Site.items import WedropCatalogItem

            now = datetime.datetime.now()
            timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

            loader = ItemLoader(item=WedropCatalogItem(), selector=selector)

            loader.add_value('url', response.url)
            loader.add_value('category', category_name)
            loader.add_value('scrape_time', timestamp_str)

            # Extract product ID from URL
            product_id_match = re.search(r'/catalog/(\d+)', response.url)
            if product_id_match:
                loader.add_value('product_id', product_id_match.group(1))

            # Extract title
            title_selectors = [
                'h1::text',
                'h2::text',
                'title::text',
                '[class*="title"]::text',
            ]
            for title_sel in title_selectors:
                title = selector.css(title_sel).get()
                if title and clean_text(title):
                    loader.add_value('title', clean_text(title))
                    break

            # Extract CNPJ
            cnpj_selectors = [
                'text=CNPJ',
                '[class*="cnpj"]::text',
                '[class*="CNPJ"]::text',
            ]
            for cnpj_sel in cnpj_selectors:
                cnpj_text = selector.xpath(f"//*[contains(text(), 'CNPJ')]/text()").getall()
                if cnpj_text:
                    cnpj_match = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', " ".join(cnpj_text))
                    if cnpj_match:
                        loader.add_value('cnnpj', cnpj_match.group(0))
                        break

            # Extract Estado de Origem
            estado_text = selector.xpath("//*[contains(text(), 'Estado')]/text()").getall()
            if estado_text:
                estado_match = re.search(r'[A-Z]{2}', " ".join(estado_text))
                if estado_match:
                    loader.add_value('estado_origem', estado_match.group(0))

            # Extract sales history
            vendas_text = selector.xpath("//*[contains(text(), 'vendas')]/text()").getall()
            if vendas_text:
                vendas_match = re.search(r'(\d+)', " ".join(vendas_text))
                if vendas_match:
                    loader.add_value('numero_vendas', vendas_match.group(0))

            # Extract stock history
            stock_history_entries = []
            stock_history_selectors = [
                '[class*="history"]',
                '[class*="History"]',
                '[class*="stock"]',
                '[class*="Stock"]',
            ]
            
            for sh_sel in stock_history_selectors:
                history_elements = selector.css(sh_sel)
                if history_elements:
                    for elem in history_elements:
                        text = elem.css('::text').getall()
                        text_content = " ".join([t.strip() for t in text if t.strip()])
                        if text_content:
                            stock_history_entries.append(text_content)
                    if stock_history_entries:
                        break

            loader.add_value('stock_history', " | ".join(stock_history_entries) if stock_history_entries else '')

            # Determine if active - look for indicators
            is_active = True
            inactive_indicators = ['desativado', 'inativo', 'deactivated', 'inactive']
            page_text = " ".join(selector.css('::text').getall()).lower()
            for indicator in inactive_indicators:
                if indicator in page_text:
                    is_active = False
                    break
            
            loader.add_value('is_active', 'Sim' if is_active else 'Não')

            # Extract total stock count and real balance
            stock_count_match = re.search(r'(\d+)\s*(unidades?|itens?|items?)', page_text, re.I)
            if stock_count_match:
                loader.add_value('total_stock_count', stock_count_match.group(1))
                # Real balance would be total if active, 0 if inactive
                loader.add_value('real_balance', stock_count_match.group(1) if is_active else '0')
            else:
                loader.add_value('total_stock_count', '0')
                loader.add_value('real_balance', '0')

            try:
                await page.close()
            except:
                pass

            item = loader.load_item()
            self.log(f"\u2705 Produto {item.get('product_id', 'N/A')} raspado: {item.get('title', 'Sem titulo')[:50]}...")
            yield item

        except Exception as parse_error:
            self.log(f"❌ ERRO CRÍTICO no parse_product(): {parse_error}", level=logging.ERROR)
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", level=logging.ERROR)
            try:
                page = response.meta.get("playwright_page")
                if page:
                    await page.close()
            except:
                pass
