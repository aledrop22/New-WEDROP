from scrapy import signals
from scrapy.exceptions import IgnoreRequest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class SeleniumMiddleware:
    """Custom Selenium Middleware compatível com Selenium 3.x"""

    def __init__(self, crawler):
        self.driver = None
        crawler.signals.connect(self.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def spider_opened(self, spider):
        """Inicializa o ChromeDriver quando a spider abre"""
        driver_path = ChromeDriverManager().install()
        
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Selenium 3.x usa 'executable_path' diretamente
        self.driver = webdriver.Chrome(
            executable_path=driver_path,
            chrome_options=chrome_options
        )
        spider.driver = self.driver

    def spider_closed(self, spider):
        """Fecha o ChromeDriver quando a spider fecha"""
        if self.driver:
            self.driver.quit()

    def process_request(self, request, spider):
        """Processa requisições do Scrapy com Selenium"""
        if request.meta.get('selenium_request'):
            self.driver.get(request.url)
            
            # Injeta cookies se necessário
            if request.meta.get('inject_cookies'):
                spider._inject_cookies(self.driver)

            # Disponibiliza o driver no meta da resposta
            request.meta['driver'] = self.driver
            
            # Espera por elementos se necessário
            if request.meta.get('wait_for_selector'):
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, request.meta['wait_for_selector'])
                    )
                )
            
            # Retorna o conteúdo da página
            from scrapy.http import HtmlResponse
            return HtmlResponse(
                url=self.driver.current_url,
                body=self.driver.page_source.encode('utf-8'),
                encoding='utf-8',
                request=request
            )

        return None
