# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SiteItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class WedropCatalogItem(scrapy.Item):
    # Item for WeDrop catalog products
    product_id = scrapy.Field()
    title = scrapy.Field()
    url = scrapy.Field()
    category = scrapy.Field()
    is_active = scrapy.Field()
    total_stock_count = scrapy.Field()
    real_balance = scrapy.Field()
    stock_history = scrapy.Field()
    scrape_time = scrapy.Field()
    cnnpj = scrapy.Field()
    estado_origem = scrapy.Field()
    numero_vendas = scrapy.Field()


class WedropCategoryItem(scrapy.Item):
    # Item for WeDrop categories
    category_name = scrapy.Field()
    category_count = scrapy.Field()
    category_url = scrapy.Field()
    scrape_time = scrapy.Field()
