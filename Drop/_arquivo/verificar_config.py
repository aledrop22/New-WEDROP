"""
Verificador de Configuração do Scraper
Este script valida se as correções foram aplicadas corretamente
"""

import json
import re
import sys
from pathlib import Path

def check_settings():
    """Verifica se os settings foram alterados corretamente"""
    settings_file = Path("Site/settings.py")
    
    if not settings_file.exists():
        print("❌ Arquivo Site/settings.py não encontrado!")
        return False
    
    content = settings_file.read_text()
    
    checks = {
        "CONCURRENT_REQUESTS_PER_DOMAIN = 1": "Concorrência por domínio reduzida",
        "CONCURRENT_REQUESTS = 2": "Concorrência total reduzida",
        "DOWNLOAD_DELAY = 1.5": "Delay aumentado",
        "DOWNLOAD_TIMEOUT = 120": "Timeout aumentado",
        "PLAYWRIGHT_MAX_CONTEXTS = 2": "Max contexts reduzido",
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 2": "Max pages por context reduzido",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 45_000": "Navigation timeout aumentado",
        "PLAYWRIGHT_BROWSER_LAUNCH_TIMEOUT = 60_000": "Browser launch timeout aumentado",
    }
    
    print("🔍 Verificando Site/settings.py...\n")
    
    all_good = True
    for check, description in checks.items():
        if check in content:
            print(f"✅ {description}")
        else:
            print(f"❌ {description} - NÃO ENCONTRADO")
            all_good = False
    
    return all_good


def check_spider():
    """Verifica se o spider foi alterado corretamente"""
    spider_file = Path("Site/spiders/wedrop.py")
    
    if not spider_file.exists():
        print("\n❌ Arquivo Site/spiders/wedrop.py não encontrado!")
        return False
    
    content = spider_file.read_text()
    
    # Contar quantas vezes page.close() aparece
    close_count = content.count("await page.close()")
    
    print("\n🔍 Verificando Site/spiders/wedrop.py...\n")
    
    if close_count >= 3:
        print(f"✅ Limpeza de memória implementada ({close_count} chamadas page.close())")
        return True
    else:
        print(f"❌ Limpeza de memória - apenas {close_count} chamadas page.close() encontradas")
        return False


def check_data_json():
    """Verifica se há dados em data.json"""
    data_file = Path("data.json")
    
    print("\n🔍 Verificando data.json...\n")
    
    if not data_file.exists():
        print("⚠️  data.json não existe ainda (execute o scraper primeiro)")
        return None
    
    try:
        with open(data_file) as f:
            lines = f.readlines()
        
        count = len(lines)
        if count > 0:
            print(f"✅ {count} itens encontrados em data.json")
            
            # Tentar carregar o primeiro item
            first_line = lines[0].strip()
            if first_line.startswith('{'):
                item = json.loads(first_line)
                if 'title' in item:
                    print(f"   • Exemplo: {item.get('title', 'Sem título')[:60]}")
            return True
        else:
            print("❌ data.json vazio (nenhum item extraído)")
            return False
    except Exception as e:
        print(f"❌ Erro ao ler data.json: {e}")
        return False


def main():
    print("=" * 60)
    print("  🔧 VERIFICADOR DE CONFIGURAÇÃO DO SCRAPER")
    print("=" * 60)
    print()
    
    settings_ok = check_settings()
    spider_ok = check_spider()
    data_ok = check_data_json()
    
    print("\n" + "=" * 60)
    print("  📊 RESUMO")
    print("=" * 60)
    print(f"Settings:  {'✅' if settings_ok else '❌'}")
    print(f"Spider:    {'✅' if spider_ok else '❌'}")
    if data_ok is None:
        print(f"Data:      ⚠️  (execute o scraper primeiro)")
    else:
        print(f"Data:      {'✅' if data_ok else '❌'}")
    
    if settings_ok and spider_ok:
        print("\n✅ Todas as correções foram aplicadas corretamente!")
        print("\n💡 Próximo passo: Execute o scraper")
        print("   python -m scrapy crawl wedrop")
        return 0
    else:
        print("\n❌ Algumas correções estão faltando!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
