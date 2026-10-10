# Scrapy settings for Site project
BOT_NAME = "Site"

SPIDER_MODULES = ["Site.spiders"]
NEWSPIDER_MODULE = "Site.spiders"

ADDONS = {}

import sys

# TWISTED REACTOR - NECESSÁRIO PARA PLAYWRIGHT
# No Windows, não definimos TWISTED_REACTOR aqui - deixamos o spider configurar o ProactorEventLoop
if sys.platform != "win32":
    TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Concorrência (REDUZIDO PARA ESTABILIDADE)
CONCURRENT_REQUESTS_PER_DOMAIN = 1  # Reduzido para evitar sobrecarga do browser
CONCURRENT_REQUESTS = 2  # Reduzido para evitar crash
DOWNLOAD_DELAY = 1.5  # Aumentado para dar tempo ao browser

# Timeouts
DOWNLOAD_TIMEOUT = 120  # Aumentado de 60 para 120 segundos

# LIMITE PARA TESTES (descomente para testar com poucas páginas)
# CLOSESPIDER_PAGECOUNT = 3  # Parar após 3 páginas de listagem (remova esta linha para full scrape)
# CLOSESPIDER_ITEMCOUNT = 100  # Parar após 100 itens

# Pipelines
ITEM_PIPELINES = {
    'Site.pipelines.SplitStockPipeline': 200,
    'Site.pipelines.WedropCatalogPipeline': 300,
}

FEED_EXPORT_ENCODING = "utf-8"

# Export incremental a cada 20 itens (desativado, usamos JSON Lines contínuo)
# FEED_EXPORT_BATCH_ITEM_COUNT = 20
# --- PLAYWRIGHT ---

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": [
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-sync",
        "--disable-translate",
    ],
}

# Desabilitar subprocessos no Windows para evitar incompatibilidade com AsyncioSelectorReactor
if sys.platform == "win32":
    PLAYWRIGHT_LAUNCH_OPTIONS["handle_sigint"] = False

# Timeouts/playwright (aumentados para maior estabilidade)
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 45_000  # 45s
PLAYWRIGHT_BROWSER_LAUNCH_TIMEOUT = 60_000  # 60s

# Limitar contexts/páginas para reduzir memória
PLAYWRIGHT_MAX_CONTEXTS = 2  # Reduzido de 4 para 2
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 2  # Reduzido de 4 para 2