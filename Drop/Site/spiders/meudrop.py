import scrapy
from scrapy_playwright.page import PageMethod
from parsel import Selector
import re
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose
import time
import os
import datetime
import logging

SITE_HOST = "meudropbrasil.com"
STORAGE_STATE_FILE = 'storage_state.json'

def clean_text(text):
    if text:
        return text.strip()
    return None

class ProductItem(scrapy.Item):
    title = scrapy.Field(output_processor=TakeFirst())
    price = scrapy.Field(output_processor=TakeFirst())
    stock = scrapy.Field(output_processor=TakeFirst())
    url = scrapy.Field(output_processor=TakeFirst())
    product_id = scrapy.Field(output_processor=TakeFirst())
    scrape_time = scrapy.Field(output_processor=TakeFirst()) 
    status_liquidacao = scrapy.Field(output_processor=TakeFirst())
    numero_vendas = scrapy.Field(output_processor=TakeFirst())

class MeudropSpider(scrapy.Spider):
    name = "meudrop"
    allowed_domains = [SITE_HOST]
    start_urls = [f"https://{SITE_HOST}/loja/"]

    custom_settings = {
        'PLAYWRIGHT_ABORT_REQUEST': lambda r: r.resource_type in ("image", "media", "font"),
    }
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(MeudropSpider, cls).from_crawler(crawler, *args, **kwargs)

        if not os.path.exists(STORAGE_STATE_FILE):
            raise ValueError(f"!!! ERRO: Ficheiro '{STORAGE_STATE_FILE}' não encontrado! Execute o 'obter_cookie.py' primeiro. !!!")
            
        spider.storage_state = STORAGE_STATE_FILE
        spider.log(f"Storage state carregado de '{STORAGE_STATE_FILE}'.")
        spider.page_count = 0
        return spider

    # CORRIGIDO: usar start_requests em vez de async start
    def start_requests(self):
        url = self.start_urls[0]
        timestamp = int(time.time() * 1000)
        cache_busted_url = f"{url}?cache_buster={timestamp}"
        self.log(f"Iniciando com cache buster: {cache_busted_url}")
        
        yield scrapy.Request(
            cache_busted_url, 
            callback=self.parse,
            errback=self.parse_listing_error,
            dont_filter=True,
            meta=dict(
                playwright=True,
                playwright_stealth=True,
                playwright_include_page=True,
                playwright_context_kwargs={'storage_state': self.storage_state},
                playwright_page_goto_kwargs=dict(
                    wait_until="domcontentloaded",
                    timeout=30000 
                ),
                playwright_page_methods=[
                    PageMethod("wait_for_selector", "ul.products", timeout=10000) 
                ]
            )
        )

    async def parse_listing_error(self, failure):
        self.log(f"ERRO ao carregar listagem: {failure.request.url} - {failure.value}", level=logging.ERROR)
        page = failure.request.meta.get("playwright_page")
        if page:
            try:
                await page.close()
            except:
                pass

    async def parse(self, response):
        self.page_count += 1
        self.log(f"=== PÁGINA {self.page_count}: {response.url} ===")

        page = response.meta["playwright_page"]
        
        try:
            await page.wait_for_selector("ul.products li.product", timeout=10000)
            
            try:
                self.log(f"Esperando tags 'Mais Vendido'...")
                await page.wait_for_selector("div.tag-vendas-produto", timeout=3000)
            except:
                self.log(f"Nenhuma tag 'Mais Vendido' (timeout 3s).")

            page_content = await page.content()
            selector = Selector(text=page_content)

        except Exception as e:
            self.log(f"ERRO: Lista de produtos não carregou na Página {self.page_count}. {e}", level=logging.ERROR)
            await page.close()
            return

        products = selector.css('li.product')
        self.log(f"Produtos encontrados: {len(products)}")

        storage_state = self.storage_state
        
        # CORRIGIDO: contador de estoque zero consecutivo
        zero_stock_counter = 0
        stop_pagination = False 
        
        for product_count, product in enumerate(products, 1):
            class_string = product.attrib.get('class', '')
            is_out_of_stock = 'outofstock' in class_string

            if is_out_of_stock:
                zero_stock_counter += 1
                title = product.css('h2.woocommerce-loop-product__title::text').get()
                self.log(f"Produto SEM estoque ({zero_stock_counter}/3): {title}")
            else:
                # Reseta contador se encontrar produto COM estoque
                zero_stock_counter = 0
                
                product_url = product.css('a.woocommerce-LoopProduct-link::attr(href)').get()
                title = product.css('h2.woocommerce-loop-product__title::text').get()

                if product_url:
                    texto_vendas_nodes = product.css('div.tag-vendas-produto::text').getall()
                    numero_de_vendas = '0' 
                    if texto_vendas_nodes:
                        full_text = " ".join(texto_vendas_nodes)
                        match = re.search(r'\d+', full_text) 
                        if match:
                            numero_de_vendas = match.group(0)

                    meta_data = dict(
                        product_title=clean_text(title) if title else 'Sem Titulo',
                        numero_de_vendas=numero_de_vendas, 
                        playwright=True,
                        playwright_stealth=True, 
                        playwright_context_kwargs={'storage_state': storage_state},
                        playwright_page_goto_kwargs=dict(
                            wait_until="domcontentloaded",
                            timeout=30000
                        ),
                        playwright_page_methods=[
                            PageMethod("wait_for_timeout", 1000), 
                        ],
                        playwright_include_page=True,
                        product_index=product_count,
                        is_retry=False
                    )
                    
                    yield scrapy.Request(
                        product_url,
                        callback=self.parse_product,
                        errback=self.parse_product_error,
                        meta=meta_data,
                        priority=0 
                    )
            
            # CORRIGIDO: parar somente após 3 consecutivos
            if zero_stock_counter >= 3:
                self.log("="*50)
                self.log(f"3 PRODUTOS CONSECUTIVOS SEM ESTOQUE ENCONTRADOS.")
                self.log(f"INTERROMPENDO RASPAGEM.")
                self.log("="*50)
                stop_pagination = True
                break
        
        # CORRIGIDO: Paginação REATIVADA
        if stop_pagination:
            self.log("PAGINAÇÃO INTERROMPIDA (regra de estoque zero).")
            await page.close()
            return 

        seletor_proxima_pagina = 'a.next.page-numbers::attr(href)'
        next_page_url = selector.css(seletor_proxima_pagina).get()

        await page.close()
        
        if next_page_url:
            self.log(f">>> Próxima página encontrada: {next_page_url}")
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                errback=self.parse_listing_error,
                dont_filter=True,
                meta=dict(
                    playwright=True,
                    playwright_stealth=True,
                    playwright_include_page=True,
                    playwright_context_kwargs={'storage_state': self.storage_state},
                    playwright_page_goto_kwargs=dict(
                        wait_until="domcontentloaded",
                        timeout=30000 
                    ),
                    playwright_page_methods=[
                        PageMethod("wait_for_selector", "ul.products", timeout=10000)
                    ]
                )
            )
        else:
            self.log("=" * 50)
            self.log("PAGINAÇÃO CONCLUÍDA. Botão 'Próxima' não encontrado.")
            self.log(f"Total de {self.page_count} páginas lidas.")
            self.log("=" * 50)

    async def parse_product(self, response):
        self.log(f"Extraindo produto: {response.url}")
        page = response.meta["playwright_page"]
        
        try:
            await page.evaluate("() => { const btn = document.querySelector('button#webbex-arp-entendido'); if (btn) btn.click(); }")
            await page.wait_for_timeout(500)
        except:
            pass

        try:
            await page.wait_for_selector("p.price, button[name='add-to-cart']", timeout=10000) 
        except Exception:
            self.log(f"ERRO: Preço não encontrado em {response.url}. Cookie expirado?", level=logging.ERROR)
            await page.close()
            return

        tags_list = []
        try:
            tag_locators = page.locator('span.tagged_as span.detail-content a')
            await tag_locators.first.wait_for(timeout=3000) 
            for tag in await tag_locators.all():
                tag_text = await tag.text_content()
                if tag_text:
                    tags_list.append(tag_text.strip().lower()) 
        except:
            pass

        page_content = await page.content()
        await page.close()

        selector = Selector(text=page_content)
        loader = ItemLoader(item=ProductItem(), selector=selector)
        
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        loader.add_value('scrape_time', timestamp_str)

        loader.add_value('title', response.meta.get('product_title'))
        if loader.get_output_value('title') in ['Sem Titulo', None] or 'produto' in loader.get_output_value('title').lower():
            loader.replace_css('title', 'h1.product_title::text', MapCompose(clean_text))
        loader.add_value('url', response.url)

        price_texts_raw = selector.css('p.price *::text, div.summary .price *::text, .amount::text').getall()
        price = None
        for text in price_texts_raw:
            match = re.search(r'(\d[\d\.,]*)', text)
            if match:
                cleaned_price = match.group(0).replace('.', '').replace(',', '.')
                if re.match(r'^\d+\.\d{2}$', cleaned_price) or re.match(r'^\d+$', cleaned_price.split('.')[0]):
                    price = cleaned_price
                    break
        loader.add_value('price', price if price else '0.00')
        if not price:
            self.log(f"AVISO: Preço não encontrado em {response.url}.") 

        stock_raw = selector.css('p.stock::text').get()
        stock = '0'
        if stock_raw:
            stock_match = re.search(r'\d+', stock_raw)
            if stock_match:
                stock = stock_match.group(0)
            elif 'em estoque' in stock_raw.lower() or 'in stock' in stock_raw.lower():
                stock = '1'
        loader.add_value('stock', stock)

        product_id_value = selector.css('button[name="add-to-cart"]::attr(value)').get()
        if product_id_value:
            loader.add_value('product_id', product_id_value)
        else:
            self.log(f"AVISO: Product ID não encontrado em {response.url}")
            loader.add_css('product_id', 'a.single_add_to_cart_button::attr(data-product_id)')

        if 'liquidacao' in tags_list:
            loader.add_value('status_liquidacao', 'Sim')
        else:
            loader.add_value('status_liquidacao', 'Não')
        
        numero_vendas = response.meta.get('numero_de_vendas', '0')
        loader.add_value('numero_vendas', numero_vendas)
        
        yield loader.load_item()

    async def parse_product_error(self, failure):
        request = failure.request
        url = request.url

        page = failure.request.meta.get("playwright_page")
        if page:
            try:
                await page.close()
            except:
                pass

        if request.meta.get('is_retry', False):
            self.log(f"ERRO FINAL: {url} falhou na retry. DESISTINDO.", level=logging.ERROR)
            return
        else:
            self.log(f"AVISO: Timeout em {url}. Reagendando...", level=logging.WARNING)
            request.meta['is_retry'] = True
            yield scrapy.Request(
                url=url,
                callback=self.parse_product,
                errback=self.parse_product_error,
                meta=request.meta,
                dont_filter=True, 
                priority=-10 
            )