import scrapy
import datetime
from Site.items import WedropCatalogItem, WedropCategoryItem

class WedropSimpleSpider(scrapy.Spider):
    name = "wedrop_simple"
    allowed_domains = ["dash.wedrop.com.br"]
    start_urls = ["https://dash.wedrop.com.br/catalog"]

    def parse(self, response):
        self.log(f"Visitando: {response.url}")
        self.log(f"Status: {response.status}")
        self.log(f"Comprimento do conteúdo: {len(response.body)}")

        # Salvar o HTML para debug
        with open('debug_catalog.html', 'wb') as f:
            f.write(response.body)

        # Tentar extrair categorias
        # Primeiro, vamos ver a estrutura do HTML
        self.log("Salvando HTML em debug_catalog.html para análise")

        yield {'url': response.url, 'status': response.status, 'content_length': len(response.body)}
