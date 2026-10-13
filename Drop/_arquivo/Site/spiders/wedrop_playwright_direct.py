import asyncio
import scrapy
import json
from Site.items import WedropCatalogItem, WedropCategoryItem
from playwright.async_api import async_playwright
import datetime

class WedropPlaywrightDirectSpider(scrapy.Spider):
    name = "wedrop_playwright_direct"
    allowed_domains = ["dash.wedrop.com.br"]
    start_urls = ["https://dash.wedrop.com.br/catalog"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.playwright = None
        self.browser = None
        self.context = None

    async def init_playwright(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()
            # Carregar storage state se existir
            try:
                await self.context.add_cookies(json.load(open('storage_state.json')).get('cookies', []))
                self.log("Cookies carregados do storage_state.json")
            except:
                self.log("Não foi possível carregar cookies")

    async def close_playwright(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def start_requests(self):
        # Não usamos start_requests normais, vamos usar Playwright
        return scrapy.Request('https://dash.wedrop.com.br/catalog', callback=self.parse, dont_filter=True)

    async def parse(self, response):
        await self.init_playwright()

        page = await self.context.new_page()
        await page.goto('https://dash.wedrop.com.br/catalog', wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)

        content = await page.content()
        self.log(f"Comprimento do conteúdo: {len(content)}")

        # Salvar para debug
        with open('debug_catalog_playwright.html', 'w', encoding='utf-8') as f:
            f.write(content)

        await page.close()
        await self.close_playwright()

        yield {'url': response.url, 'content_length': len(content)}
