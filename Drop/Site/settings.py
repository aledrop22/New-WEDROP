# Scrapy settings for Site project
BOT_NAME = "Site"

SPIDER_MODULES = ["Site.spiders"]
NEWSPIDER_MODULE = "Site.spiders"

ADDONS = {}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concorrência (MODO LENTO E SEGURO)
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# Pipeline (desativada, o que é o correto)
ITEM_PIPELINES = {
   # 'Site.pipelines.GoogleSheetsBatchPipeline': 300,
}

FEED_EXPORT_ENCODING = "utf-8"

# --- ATIVAÇÃO DO PLAYWRIGHT (COM A CORREÇÃO DO 'https') ---
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler", # <-- Corrigido (sem o '_')
}
# Esta linha é OBRIGATÓRIA para o Playwright funcionar
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor" 

# --- OPÇÕES DO NAVEGADOR (VERSÃO ESTÁVEL) ---
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True
}

PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 1