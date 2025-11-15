import scrapy
from scrapy_playwright.page import PageMethod
from parsel import Selector
import re
from scrapy.loader import ItemLoader
from itemloaders.processors import TakeFirst, MapCompose
import time
import os
import datetime # Adicionado para o timestamp
import logging  # Adicionado para logar retentativas

SITE_HOST = "meudropbrasil.com"
STORAGE_STATE_FILE = 'storage_state.json' # Para carregar o estado completo

# Função para limpar espaços em branco
def clean_text(text):
    if text:
        return text.strip()
    return None

class ProductItem(scrapy.Item):
    # Campos que o scraper irá coletar
    item_number = scrapy.Field(output_processor=TakeFirst())
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

    # Bloqueia recursos desnecessários (mantém o CSS para a lógica de 'strike' funcionar)
    custom_settings = {
        'PLAYWRIGHT_ABORT_REQUEST': lambda r: r.resource_type in ("image", "media", "font"),
    }
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(MeudropSpider, cls).from_crawler(crawler, *args, **kwargs)

        # --- LÓGICA DO STORAGE STATE (ESTÁVEL) ---
        if not os.path.exists(STORAGE_STATE_FILE):
            raise ValueError(f"!!! ERRO: Ficheiro '{STORAGE_STATE_FILE}' não encontrado! Execute o 'obter_cookie.py' primeiro. !!!")
            
        spider.storage_state = STORAGE_STATE_FILE
        spider.log(f"Storage state carregado de '{STORAGE_STATE_FILE}'. Cookies e localStorage incluídos.")
        # --- FIM LÓGICA DO STORAGE STATE ---

        spider.page_count = 0
        return spider

    # --- FUNÇÃO 1 (START): USA PLAYWRIGHT E STORAGE STATE ---
    async def start(self):
        url = self.start_urls[0]
        timestamp = int(time.time() * 1000)
        cache_busted_url = f"{url}?cache_buster={timestamp}"
        self.log(f"Usando URL com Cache Buster: {cache_busted_url}")
        
        yield scrapy.Request(
            cache_busted_url, 
            callback=self.parse, 
            dont_filter=True,
            meta=dict(
                playwright=True,
                playwright_stealth=True,
                playwright_include_page=True,
                playwright_context_kwargs={'storage_state': self.storage_state}, # Injeta o login
                playwright_page_goto_kwargs=dict(
                    wait_until="domcontentloaded",
                    timeout=30000 
                ),
                playwright_page_methods=[
                    PageMethod("wait_for_selector", "ul.products", timeout=10000) 
                ]
            )
        )

    # --- FUNÇÃO 2 (PARSE): RASPAGEM E LÓGICA DE PARADA ---
    async def parse(self, response):
        self.page_count += 1
        self.log(f"Iniciando o parse da listagem [PÁGINA {self.page_count}]: {response.url}")

        page = response.meta["playwright_page"]
        
        try:
            await page.wait_for_selector("ul.products li.product", timeout=10000)
            
            try:
                self.log(f"Esperando por tags 'Mais Vendido' (JS)...")
                await page.wait_for_selector("div.tag-vendas-produto", timeout=3000)
                self.log(f"Tags 'Mais Vendido' encontradas.")
            except Exception:
                self.log(f"AVISO: Nenhuma tag 'Mais Vendido' encontrada apos 3s (Pagina {self.page_count}).")

            page_content = await page.content()
            selector = Selector(text=page_content)

        except Exception as e:
            self.log(f"ERRO: Nao foi possivel carregar a lista de produtos na Pagina {self.page_count}. {e}", level=logging.ERROR)
            await page.close()
            return

        products = selector.css('li.product')
        self.log(f"Produtos encontrados nesta pagina: {len(products)}")
        if not products:
            self.log("Nenhum link de produto encontrado nesta pagina.")

        storage_state = self.storage_state
        
        zero_stock_counter = 0
        stop_pagination = False 
        
        for product_count, product in enumerate(products, 1):
            
            class_string = product.attrib.get('class', '')
            is_out_of_stock = 'outofstock' in class_string

            if is_out_of_stock:
                zero_stock_counter += 1
                self.log(f"Produto sem estoque encontrado (Strike {zero_stock_counter}/3): {product.css('h2.woocommerce-loop-product__title::text').get()}")
            else:
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
                        playwright_context_kwargs={'storage_state': storage_state}, # Injeta o login
                        playwright_page_goto_kwargs=dict(
                            wait_until="domcontentloaded",
                            timeout=30000 # <-- Reduzido para 30s
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
                    
            if zero_stock_counter >= 3:
                self.log("="*50)
                self.log(f"3 PRODUTOS CONSECUTIVOS COM ESTOQUE ZERO ENCONTRADOS.")
                self.log(f"INTERROMPENDO A RASPAGEM DA LOJA.")
                self.log("="*50)
                stop_pagination = True 
                break 
        
        # --- LÓGICA DE PAGINAÇÃO (REATIVADA) ---
        self.log(f"Procurando pela proxima pagina (botao 'next')...")
        
        if stop_pagination:
            self.log("PAGINAÇÃO INTERROMPIDA DEVIDO A REGRA DE ESTOQUE ZERO.")
            await page.close()
            return 

        seletor_proxima_pagina = 'a.next.page-numbers::attr(href)'
        next_page_url = selector.css(seletor_proxima_pagina).get()

        await page.close() # Fecha a pagina de listagem atual
        
        if next_page_url:
            self.log(f"Proxima pagina (Pagina {self.page_count + 1}) encontrada: {next_page_url}")
            # Chama a função 'parse' novamente com a próxima URL
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,
                dont_filter=True,
                meta=dict(
                    playwright=True,
                    playwright_stealth=True,
                    playwright_include_page=True,
                    playwright_context_kwargs={'storage_state': self.storage_state}, # Injeta o login
                    playwright_page_goto_kwargs=dict(
                        wait_until="domcontentloaded",
                        timeout=30000 # <-- Reduzido para 30s
                    ),
                    playwright_page_methods=[
                        PageMethod("wait_for_selector", "ul.products", timeout=10000)
                    ]
                )
            )
        else:
            self.log("=" * 50)
            self.log("PAGINAÇÃO CONCLUIDA. Botao 'Proxima' nao encontrado.")
            self.log(f"Total de {self.page_count} paginas de listagem foram lidas.")
            self.log("=" * 50)


    # --- FUNÇÃO 3 (PARSE_PRODUCT) ---
    async def parse_product(self, response):
        self.log(f"Extraindo dados do produto (via Cookie): {response.url}")
        page = response.meta["playwright_page"]
        
        try: # Tenta fechar o pop-up "Entendido"
            await page.evaluate("() => { const button = document.querySelector('button#webbex-arp-entendido'); if (button) { button.click(); } }")
            await page.wait_for_timeout(500)
        except Exception: pass

        # --- ESPERA PELO PREÇO (PROVA DE LOGIN) ---
        try:
            await page.wait_for_selector(
                "p.price, button[name='add-to-cart']", 
                timeout=10000
            ) 
        except Exception:
            self.log(f"ERRO CRITICO: Nao foi possivel encontrar 'p.price' ou 'add-to-cart' em {response.url}. O Cookie pode ter EXPIRADO.", level=logging.ERROR)
            await page.close()
            return # Pula este item

        # --- LÓGICA DE 'LIQUIDAÇÃO' ---
        tags_list = []
        try:
            tag_locators = page.locator('span.tagged_as span.detail-content a')
            await tag_locators.first.wait_for(timeout=3000) 
            
            for tag in await tag_locators.all():
                tag_text = await tag.text_content()
                if tag_text:
                    tags_list.append(tag_text.strip().lower()) 
                    
        except Exception:
            self.log(f"AVISO: Nenhuma tag encontrada (ou timeout) em {response.url}.")
            pass 

        # Proteger page.content() com timeout para evitar travamento
        try:
            page_content = await page.content()
        except Exception as e:
            self.log(f"ERRO ao obter conteúdo da página {response.url}: {e}")
            page_content = await page.evaluate("() => document.documentElement.outerHTML")
        
        # Fechar página com proteção contra erros de shutdown
        try:
            await page.close()
        except Exception as e:
            self.log(f"AVISO: Não foi possível fechar a página 'zumbi'. {e}", level=logging.WARNING)

        selector = Selector(text=page_content)
        loader = ItemLoader(item=ProductItem(), selector=selector)
        
        # Campo para numeração (será preenchido no data_export.py)
        loader.add_value('item_number', None)
        
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
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
        if not price: self.log(f"AVISO: Preço nao encontrado em {response.url}.") 

        stock_raw = selector.css('p.stock::text').get()
        stock = '0'
        if stock_raw:
            stock_match = re.search(r'\d+', stock_raw)
            if stock_match: stock = stock_match.group(0)
            elif 'em estoque' in stock_raw.lower() or 'in stock' in stock_raw.lower(): stock = '1'
        loader.add_value('stock', stock)

        product_id_value = selector.css('button[name="add-to-cart"]::attr(value)').get()
        if product_id_value: loader.add_value('product_id', product_id_value)
        else:
            self.log(f"AVISO: Product ID nao encontrado em {response.url}")
            loader.add_css('product_id', 'a.single_add_to_cart_button::attr(data-product_id)')

        # --- SALVANDO OS NOVOS DADOS ---
        
        if 'liquidacao' in tags_list:
            loader.add_value('status_liquidacao', 'Sim')
        else:
            loader.add_value('status_liquidacao', 'Não')
        
        numero_vendas = response.meta.get('numero_de_vendas', '0')
        loader.add_value('numero_vendas', numero_vendas)
        
        yield loader.load_item()

    # --- FUNÇÃO 4 (ERRBACK): LÓGICA DE RETENTATIVA (COM CORREÇÃO) ---
    async def parse_product_error(self, failure):
        request = failure.request
        meta = request.meta
        url = request.url

        # --- CORREÇÃO: FECHA A PÁGINA QUE FALHOU ---
        page = failure.request.meta.get("playwright_page")
        if page:
            try:
                await page.close()
                self.log(f"Página 'zumbi' (Timeout?) em {url} foi fechada.", level=logging.INFO)
            except Exception as e:
                self.log(f"Não foi possível fechar a página 'zumbi'. {e}", level=logging.WARNING)
        # --- FIM DA CORREÇÃO ---

        if meta.get('is_retry', False):
            self.log(f"ERRO FINAL (Passo 2): Falha ao raspar {url} mesmo na retentativa. DESISTINDO DESTE ITEM.", level=logging.ERROR)
            return

        else:
            self.log(f"AVISO (Passo 1): Falha ao baixar {url} (Timeout?). Re-agendando para o Passo 2 (prioridade baixa).", level=logging.WARNING)
            
            meta['is_retry'] = True
            
            yield scrapy.Request(
                url=url,
                callback=self.parse_product,
                errback=self.parse_product_error,
                meta=meta,
                dont_filter=True, 
                priority=-10 
            )